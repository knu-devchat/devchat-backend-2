import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import AiChatSession, AiChatMessage
from chat.models import ChatRoom
from login.models import UserProfile
from .services import get_ai_response 

User = get_user_model()

class AiChatConsumer(AsyncWebsocketConsumer): 
    async def connect(self):
        try:
            print(f"\n[AI_DEBUG] ========== AI WebSocket 연결 시도 ==========")
            
            # 1. 인증 확인
            self.user = self.scope.get('user')
            print(f"[AI_DEBUG] User: {self.user}")
            print(f"[AI_DEBUG] Is authenticated: {getattr(self.user, 'is_authenticated', False)}")
            
            if not self.user or not self.user.is_authenticated:
                print(f"[AI_ERROR] 인증 실패")
                await self.close(code=4001)
                return

            # 2. URL에서 session_id 추출
            self.session_id = self.scope["url_route"]["kwargs"].get("session_id")
            print(f"[AI_DEBUG] 추출된 Session ID: '{self.session_id}'")
            
            if not self.session_id:
                print(f"[AI_ERROR] Session ID가 없음")
                await self.close(code=4002)
                return
            
            # 3. 사용자 프로필 가져오기
            self.user_profile = await self._get_user_profile(self.user)
            if not self.user_profile:
                print(f"[AI_ERROR] UserProfile 가져오기 실패")
                await self.close(code=4001)
                return
                
            self.username = self.user.username
            print(f"[AI_DEBUG] 사용자 프로필: {self.username}")
            
            # 4. AI 세션 존재 여부 확인
            session_info = await self._get_ai_session_and_check_permission(self.session_id, self.user_profile)
            if not session_info:
                print(f"[AI_ERROR] AI 세션이 없거나 권한 없음: {self.session_id}")
                await self.close(code=4003)
                return
            
            self.ai_session = session_info['session']
            self.room = session_info['room']
            room_name = session_info['room_name']
            
            print(f"[AI_DEBUG] AI 세션 확인 완료 - 기반 방: {room_name}, Session: {self.session_id}")
            
            # 5. AI 프로필 및 사용자명 로드
            ai_profile_data = await self._get_ai_profile()
            if not ai_profile_data:
                print(f"[AI_ERROR] AI 프로필 로드 실패")
                await self.close(code=4000)
                return
            
            self.ai_profile = ai_profile_data['profile']
            self.ai_username = ai_profile_data['username']
            print(f"[AI_DEBUG] AI 프로필 로드: {self.ai_username}")
            
            # 6. 그룹 이름 설정 및 가입
            # AI 전용 그룹 (room_uuid 기반으로 같은 방의 모든 AI 채팅 사용자가 공유)
            self.ai_group_name = f"llm_chat_{self.room.room_uuid}"
            # 일반 채팅방 그룹 이름
            self.room_group_name = f"chat_{self.room.room_uuid}"
            
            await self.channel_layer.group_add(self.ai_group_name, self.channel_name)
            await self.accept()
            
            print(f"[AI_SUCCESS] ✅ AI WebSocket 연결 성공: {self.username} → AI Session {self.session_id}")
            
            # 7. 연결 안정화를 위한 짧은 지연
            import asyncio
            await asyncio.sleep(0.1)
            
            # 8. 연결 상태 확인 후 히스토리 전송
            if self.channel_name:
                print(f"[AI_DEBUG] 🔌 WebSocket 연결 상태 확인 완료, 히스토리 전송 시작")
                await self._send_message_history()
            else:
                print(f"[AI_WARNING] ⚠️ WebSocket 연결 상태 불안정, 히스토리 전송 건너뜀")
            
            # 9. AI 입장 메시지 전송 (AI 그룹에만)
            await self.channel_layer.group_send(
                self.ai_group_name,
                {
                    "type": "ai_joined",
                    "username": self.ai_username,
                    "message": f"{self.ai_username}가 대화에 참여했습니다.",
                    "timestamp": timezone.now().isoformat(),
                }
            )
            
        except Exception as e:
            print(f"[AI_ERROR] AI WebSocket 연결 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            await self.close(code=4000)
    
    async def disconnect(self, close_code):
        try:
            if hasattr(self, 'ai_group_name') and hasattr(self, 'username'):
                print(f"[AI_DEBUG] AI WebSocket 연결 종료: {self.username} (code: {close_code})")
                
                # AI 그룹에서 제거
                await self.channel_layer.group_discard(self.ai_group_name, self.channel_name)
                
        except Exception as e:
            print(f"[AI_ERROR] AI WebSocket 연결 종료 중 오류: {e}")

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
            message_type = data.get("type", "")
            
            print(f"[AI_DEBUG] AI 메시지 수신: type={message_type}, data={data}")
            
            # 프론트엔드에서 보내는 메시지 타입별 처리
            if message_type == "chat_message":
                await self._handle_chat_message(data)
            elif message_type == "get_message_history":
                await self._handle_get_message_history(data)
            else:
                print(f"[AI_WARNING] 알 수 없는 메시지 타입: {message_type}")
                
        except json.JSONDecodeError as e:
            print(f"[AI_ERROR] JSON 파싱 실패: {e}")
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "잘못된 메시지 형식입니다."
            }))
        except Exception as e:
            print(f"[AI_ERROR] 메시지 처리 실패: {e}")
            import traceback
            traceback.print_exc()

    async def _handle_chat_message(self, data):
        """사용자 채팅 메시지 처리 및 AI 응답 생성"""
        message = data.get("message", "").strip()
        if not message:
            print(f"[AI_WARNING] 빈 메시지 무시")
            return

        # 메시지 길이 제한
        if len(message) > 2000:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "메시지가 너무 깁니다. (최대 2000자)"
            }))
            return

        print(f"[AI_DEBUG] 사용자 메시지 처리: {self.username} → {message[:50]}...")

        # 1. 사용자 메시지 AI 전용 DB에 저장
        stored_message = await self._save_ai_message(self.ai_session, self.user_profile, message, is_ai=False)
        
        if not stored_message:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "메시지 저장 중 오류가 발생했습니다."
            }))
            return
        
        # 2. 사용자 메시지를 AI 그룹에만 브로드캐스트
        await self.channel_layer.group_send(
            self.ai_group_name,
            {
                "type": "chat_message",
                "message": message,
                "username": self.username,
                "message_id": stored_message.id,
                "timestamp": stored_message.created_at.isoformat(),
                "sender_id": self.user_profile.id,
                "is_ai": False,
            }
        )
        
        print(f"[AI_DEBUG] 사용자 메시지 브로드캐스트 완료 (AI 그룹만)")
        
        # 3. AI 처리 시작 표시 (AI 그룹에만)
        await self.channel_layer.group_send(
            self.ai_group_name,
            {
                "type": "ai_thinking",
                "username": self.ai_username,
            }
        )
        
        # 4. AI 응답 생성 및 전송
        await self._process_ai_request(message)

    async def _handle_get_message_history(self, data):
        """메시지 히스토리 요청 처리"""
        try:
            page = data.get("page", 1)
            limit = min(data.get("limit", 50), 100)  # 최대 100개로 제한
            
            print(f"[AI_DEBUG] 메시지 히스토리 요청: page={page}, limit={limit}")
            
            # 페이지네이션을 고려한 히스토리 조회
            offset = (page - 1) * limit
            history_messages = await self._get_paginated_message_history(self.ai_session, offset, limit)
            total_count = await self._get_total_message_count(self.ai_session)
            
            # 페이지네이션 정보 계산
            total_pages = (total_count + limit - 1) // limit
            has_next = page < total_pages
            has_previous = page > 1
            
            # 히스토리 응답 전송
            await self.send(text_data=json.dumps({
                "type": "message_history",
                "messages": history_messages,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_messages": total_count,
                    "has_next": has_next,
                    "has_previous": has_previous
                },
                "session_id": self.session_id
            }))
            
            print(f"[AI_DEBUG] 메시지 히스토리 응답 완료: {len(history_messages)}개 메시지")
            
        except Exception as e:
            print(f"[AI_ERROR] 메시지 히스토리 요청 처리 실패: {e}")
            import traceback
            traceback.print_exc()
            
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "메시지 히스토리를 불러올 수 없습니다."
            }))

    async def _process_ai_request(self, user_message: str):
        """AI 응답 생성 및 전송"""
        try:
            print(f"[AI_DEBUG] AI 응답 생성 시작...")
            
            # 최근 대화 히스토리 가져오기 (AI 전용 테이블에서)
            recent_history = await self._get_recent_messages_from_db(self.ai_session, limit=10)

            # AI 페르소나 설정 및 전체 대화 기록 구성
            ai_persona = {
                "role": "system", 
                "content": "당신은 개발자 채팅방에 참여한 친절하고 전문적인 AI 어시스턴트입니다. 항상 한국어로 답변하며, 코드 관련 질문에는 구체적이고 실용적인 조언을 제공합니다."
            }
            full_history = [ai_persona] + recent_history + [{"role": "user", "content": user_message}]
            
            print(f"[AI_DEBUG] 대화 히스토리: {len(recent_history)}개 메시지")

            # AI 서비스 호출
            ai_text = await get_ai_response(full_history)
            
            if not ai_text:
                raise Exception("AI 응답이 비어있습니다.")
            
            print(f"[AI_DEBUG] AI 응답 생성 완료: {ai_text[:50]}...")

            # AI 응답을 전용 DB에 저장
            stored_response = await self._save_ai_message(self.ai_session, self.ai_profile, ai_text, is_ai=True)
            
            if not stored_response:
                raise Exception("AI 응답 저장 실패")
            
            # AI 응답을 AI 그룹에만 브로드캐스트
            await self.channel_layer.group_send(
                self.ai_group_name,
                {
                    "type": "chat_message",
                    "message": ai_text,
                    "username": self.ai_username,
                    "message_id": stored_response.id,
                    "timestamp": stored_response.created_at.isoformat(),
                    "sender_id": self.ai_profile.id,
                    "is_ai": True,
                }
            )
            
            print(f"[AI_DEBUG] AI 응답 브로드캐스트 완료 (AI 그룹만)")
            
        except Exception as e:
            print(f"[AI_ERROR] AI 응답 생성 중 오류: {e}")
            import traceback
            traceback.print_exc()
            
            # 에러 메시지 전송 (AI 그룹에만)
            await self.channel_layer.group_send(
                self.ai_group_name,
                {
                    "type": "ai_error",
                    "message": "AI 응답 생성 중 오류가 발생했습니다.",
                }
            )


    # ==================== WebSocket 이벤트 핸들러들 ====================
    
    async def chat_message(self, event):
        """채팅 메시지 전송 - AI와 사용자 메시지 모두 처리"""
        # 현재 사용자가 메시지 발송자인지 확인
        is_self = event.get("sender_id") == self.user_profile.id
        is_ai = event.get("is_ai", False)
        
        message_data = {
            "type": "chat_message",
            "message": event.get("message"),
            "username": event.get("username"),
            "message_id": event.get("message_id"),
            "timestamp": event.get("timestamp"),
            "is_self": is_self,
            "is_ai": is_ai,
        }
        
        print(f"[AI_DEBUG] 메시지 전송: {self.username} ← {event.get('username')}: {event.get('message', '')[:50]}...")
        
        await self.send(text_data=json.dumps(message_data))

    async def ai_joined(self, event):
        """AI 참여 알림"""
        join_data = {
            "type": "ai_joined",
            "message": event.get("message"),
            "username": event.get("username"),
            "timestamp": event.get("timestamp"),
        }
        
        print(f"[AI_DEBUG] AI 참여 알림: {join_data}")
        
        await self.send(text_data=json.dumps(join_data))

    async def ai_thinking(self, event):
        """AI 생각 중 표시"""
        thinking_data = {
            "type": "ai_thinking",
            "username": event.get("username"),
        }
        
        print(f"[AI_DEBUG] AI 생각 중...")
        
        await self.send(text_data=json.dumps(thinking_data))

    async def ai_error(self, event):
        """AI 에러 알림"""
        error_data = {
            "type": "ai_error",
            "message": event.get("message"),
        }
        
        print(f"[AI_DEBUG] AI 에러 알림: {event.get('message')}")
        
        await self.send(text_data=json.dumps(error_data))

    # ==================== 데이터베이스 접근 함수들 ====================
    
    @database_sync_to_async
    def _get_user_profile(self, user):
        """사용자 프로필 가져오기/생성"""
        try:
            profile, created = UserProfile.objects.get_or_create(user=user)
            if created:
                print(f"[AI_DEBUG] 새 UserProfile 생성: {user.username}")
            else:
                print(f"[AI_DEBUG] UserProfile 조회 성공: {user.username}")
            return profile
        except Exception as e:
            print(f"[AI_ERROR] UserProfile 조회 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    @database_sync_to_async
    def _get_ai_session_and_check_permission(self, session_id: str, user_profile: UserProfile):
        """AI 세션 존재 여부 및 권한 확인"""
        try:
            print(f"[AI_DEBUG] AI 세션 조회 시작: {session_id}")
            
            # select_related로 관련 데이터를 한번에 가져옴
            session = AiChatSession.objects.select_related('base_room__admin__user').get(
                session_id=session_id,
                is_active=True
            )
            print(f"[AI_DEBUG] AI 세션 조회 성공: {session.base_room.room_name}")
            
            room = session.base_room
            
            # 참여 권한 확인: 방장이거나 참가자여야 함
            is_admin = room.admin == user_profile
            is_participant = user_profile in room.participants.all()
            
            print(f"[AI_DEBUG] 권한 확인 - 방장: {is_admin}, 참가자: {is_participant}")
            
            if is_admin or is_participant:
                print(f"[AI_DEBUG] ✅ AI 세션 권한 확인 완료: {user_profile.user.username}")
                
                return {
                    'session': session,
                    'room': room,
                    'room_name': room.room_name,
                    'is_admin': is_admin,
                    'is_participant': is_participant
                }
            else:
                print(f"[AI_DEBUG] ❌ AI 세션 참여 권한 없음: {user_profile.user.username}")
                return None
                
        except AiChatSession.DoesNotExist:
            print(f"[AI_DEBUG] ❌ AI 세션이 존재하지 않음: {session_id}")
            return None
        except Exception as e:
            print(f"[AI_ERROR] AI 세션 조회 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    @database_sync_to_async
    def _get_ai_profile(self):
        """AI 봇을 위한 UserProfile 객체를 가져옵니다. (없으면 생성)"""
        try:
            # AI 전용 User 및 UserProfile 생성 또는 조회
            ai_user, created = User.objects.get_or_create(
                username='AI_Assistant',
                defaults={
                    'is_active': False,  # 로그인 불가능하도록 설정
                    'email': 'ai@devchat.local',
                    'first_name': 'AI',
                    'last_name': 'Assistant'
                }
            )
            if created:
                print(f"[AI_DEBUG] AI User 생성: {ai_user.username}")
            
            ai_profile, created = UserProfile.objects.get_or_create(user=ai_user)
            if created:
                print(f"[AI_DEBUG] AI UserProfile 생성: {ai_user.username}")
            else:
                print(f"[AI_DEBUG] AI UserProfile 조회 성공: {ai_user.username}")
            
            # username을 여기서 미리 가져와서 반환 (async context에서 접근 방지)
            return {
                'profile': ai_profile,
                'username': ai_user.username
            }
            
        except Exception as e:
            print(f"[AI_ERROR] AI 프로필 조회/생성 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
        
    @database_sync_to_async
    def _save_ai_message(self, session: AiChatSession, sender: UserProfile, content: str, is_ai: bool = False):
        """AI 전용 테이블에 메시지 저장"""
        try:
            message = AiChatMessage.objects.create(
                session=session,
                sender=sender, 
                content=content,
                is_ai_message=is_ai,
                created_at=timezone.now()
            )
            msg_type = "AI" if is_ai else "User"
            print(f"[AI_DEBUG] {msg_type} 메시지 저장 성공: {sender.user.username} → {content[:50]}...")
            return message
        except Exception as e:
            print(f"[AI_ERROR] AI 메시지 저장 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    @database_sync_to_async
    def _get_recent_messages_from_db(self, session: AiChatSession, limit: int = 10):
        """AI 전용 테이블에서 최근 메시지를 가져와 OpenAI 형식으로 변환"""
        try:
            # AI 세션별 메시지 조회 (깔끔하고 빠름)
            messages = list(
                AiChatMessage.objects.filter(session=session)
                .select_related('sender__user')
                .order_by('-created_at')[:limit]
            )
            
            # 오래된 순으로 정렬 (대화 순서대로)
            messages.reverse()
            
            formatted_history = []
            
            for msg in messages:
                # is_ai_message 필드로 간단하게 구분
                role = "assistant" if msg.is_ai_message else "user"
                
                formatted_history.append({
                    "role": role, 
                    "content": msg.content
                })
            
            print(f"[AI_DEBUG] AI 전용 히스토리 조회 완료: {len(formatted_history)}개 메시지")
            return formatted_history
            
        except Exception as e:
            print(f"[AI_ERROR] AI 히스토리 조회 실패: {e}")
            import traceback
            traceback.print_exc()
            return []

    @database_sync_to_async
    def _get_message_history_for_client(self, session: AiChatSession, limit: int = 50):
        """클라이언트에게 보낼 메시지 히스토리 조회"""
        try:
            print(f"[AI_DEBUG] 🔍 DB에서 세션별 메시지 조회 시작 (세션: {session.session_id})")
            
            # AI 세션의 메시지들을 시간순으로 조회
            messages = list(
                AiChatMessage.objects.filter(session=session)
                .select_related('sender__user')
                .order_by('created_at')[:limit]  # 오래된 것부터 최신 순으로
            )
            
            print(f"[AI_DEBUG] 📊 DB 조회 결과: {len(messages)}개 메시지 발견")
            
            history_data = []
            
            for msg in messages:
                message_data = {
                    "id": msg.id,
                    "message": msg.content,
                    "username": msg.sender.user.username,
                    "timestamp": msg.created_at.isoformat(),
                    "is_ai": msg.is_ai_message,
                    "is_self": msg.sender == self.user_profile,
                }
                history_data.append(message_data)
                print(f"[AI_DEBUG] 💬 메시지 추가: {msg.sender.user.username} - {msg.content[:30]}...")
            
            print(f"[AI_DEBUG] ✅ 클라이언트용 히스토리 조회 완료: {len(history_data)}개 메시지")
            return history_data
            
        except Exception as e:
            print(f"[AI_ERROR] 💥 클라이언트 히스토리 조회 실패: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _send_message_history(self):
        """WebSocket 연결 시 기존 메시지 히스토리 전송"""
        try:
            print(f"[AI_DEBUG] 🚀 메시지 히스토리 전송 시작... (세션: {self.session_id})")
            
            # 기존 메시지 히스토리 조회
            history_messages = await self._get_message_history_for_client(self.ai_session, limit=50)
            print(f"[AI_DEBUG] 📝 히스토리 조회 결과: {len(history_messages) if history_messages else 0}개 메시지")
            
            if history_messages:
                print(f"[AI_DEBUG] 📨 {len(history_messages)}개의 기존 메시지 발견")
                
                # 📧 개별 메시지를 하나씩 전송 (안전한 방식)
                for i, msg in enumerate(history_messages):
                    try:
                        # 단일 메시지 전송
                        single_message = {
                            "type": "chat_message",
                            "message": msg["message"],
                            "username": msg["username"],
                            "timestamp": msg["timestamp"],
                            "is_ai": msg.get("is_ai", False),
                            "from_history": True  # 히스토리에서 온 메시지임을 표시
                        }
                        
                        await self.send(text_data=json.dumps(single_message))
                        print(f"[AI_DEBUG] ✅ 히스토리 메시지 전송 ({i+1}/{len(history_messages)}): {msg['username']} - {msg['message'][:20]}...")
                        
                        # 메시지 간 짧은 딜레이 (프론트엔드 처리 시간 확보)
                        import asyncio
                        await asyncio.sleep(0.01)
                        
                    except Exception as msg_error:
                        print(f"[AI_ERROR] 개별 메시지 전송 실패 ({i+1}): {msg_error}")
                        continue
                
                # 📋 히스토리 전송 완료 알림
                completion_payload = {
                    "type": "history_complete",
                    "total_messages": len(history_messages),
                    "session_id": self.session_id
                }
                await self.send(text_data=json.dumps(completion_payload))
                print(f"[AI_DEBUG] 🎉 메시지 히스토리 전송 완료: {len(history_messages)}개")
                
            else:
                print(f"[AI_DEBUG] 📭 기존 메시지 없음 - 새로운 AI 세션")
                
                # 빈 히스토리 완료 알림
                empty_payload = {
                    "type": "history_complete",
                    "total_messages": 0,
                    "session_id": self.session_id
                }
                await self.send(text_data=json.dumps(empty_payload))
                print(f"[AI_DEBUG] 📤 빈 히스토리 전송 완료")
                
        except Exception as e:
            print(f"[AI_ERROR] 💥 메시지 히스토리 전송 실패: {e}")
            import traceback
            traceback.print_exc()
            
            # 에러 시에도 완료 알림 전송 (무한 로딩 방지)
            try:
                await self.send(text_data=json.dumps({
                    "type": "history_complete", 
                    "total_messages": 0,
                    "error": "히스토리 로드 중 오류가 발생했습니다."
                }))
            except Exception as send_error:
                print(f"[AI_ERROR] 에러 메시지 전송도 실패: {send_error}")

    @database_sync_to_async
    def _get_paginated_message_history(self, session: AiChatSession, offset: int, limit: int):
        """페이지네이션을 지원하는 메시지 히스토리 조회"""
        try:
            messages = list(
                AiChatMessage.objects.filter(session=session)
                .select_related('sender__user')
                .order_by('created_at')[offset:offset + limit]  # 오래된 것부터
            )
            
            history_data = []
            for msg in messages:
                message_data = {
                    "id": msg.id,
                    "message": msg.content,
                    "username": msg.sender.user.username,
                    "timestamp": msg.created_at.isoformat(),
                    "is_ai": msg.is_ai_message,
                    "is_self": msg.sender == self.user_profile,
                }
                history_data.append(message_data)
            
            return history_data
            
        except Exception as e:
            print(f"[AI_ERROR] 페이지네이션 히스토리 조회 실패: {e}")
            return []

    @database_sync_to_async  
    def _get_total_message_count(self, session: AiChatSession):
        """AI 세션의 총 메시지 수 조회"""
        try:
            return AiChatMessage.objects.filter(session=session).count()
        except Exception as e:
            print(f"[AI_ERROR] 메시지 수 조회 실패: {e}")
            return 0