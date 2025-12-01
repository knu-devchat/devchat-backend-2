import json
import uuid
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message, UserProfile
from django.utils import timezone

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            print(f"\n[DEBUG] ========== WebSocket 연결 시도 ==========")
            
            # URL route 전체 확인
            url_route = self.scope.get("url_route", {})
            print(f"[DEBUG] URL route: {url_route}")
            print(f"[DEBUG] URL kwargs: {url_route.get('kwargs', {})}")
            
            # 1. 인증 확인
            self.user = self.scope.get('user')
            print(f"[DEBUG] User: {self.user}")
            print(f"[DEBUG] Is authenticated: {getattr(self.user, 'is_authenticated', False)}")
            
            if not self.user or not self.user.is_authenticated:
                print(f"[ERROR] 인증 실패")
                await self.close(code=4001)
                return

            # 2. UUID 추출
            room_uuid_str = self.scope["url_route"]["kwargs"].get("room_uuid")
            print(f"[DEBUG] 추출된 UUID 문자열: '{room_uuid_str}'")
            
            if not room_uuid_str:
                print(f"[ERROR] UUID가 없음")
                await self.close(code=4002)
                return
            
            # UUID 형식 검증
            try:
                self.room_uuid = uuid.UUID(room_uuid_str)
                print(f"[DEBUG] UUID 변환 성공: {self.room_uuid}")
            except ValueError as e:
                print(f"[ERROR] 잘못된 UUID 형식: {room_uuid_str} - {e}")
                await self.close(code=4002)
                return
                
            self.room_group_name = f"chat_{str(self.room_uuid)}"
            print(f"[DEBUG] 그룹 이름: {self.room_group_name}")
            
            # 3. 사용자 프로필 가져오기
            self.user_profile = await self._get_user_profile(self.user)
            if not self.user_profile:
                print(f"[ERROR] UserProfile 가져오기 실패")
                await self.close(code=4001)
                return
                
            self.username = self.user.username
            print(f"[DEBUG] 사용자 프로필: {self.username}")
            
            # 4. 채팅방 존재 여부 및 참여 권한 확인
            room_info = await self._get_room_and_check_permission(self.room_uuid, self.user_profile)
            
            if not room_info:
                print(f"[ERROR] 방이 없거나 참여 권한 없음: {self.room_uuid}")
                await self.close(code=4003)
                return
            
            self.room = room_info['room']
            admin_username = room_info['admin_username']
            room_name = room_info['room_name']
            
            print(f"[DEBUG] 권한 확인 완료 - 방: {room_name}, 방장: {admin_username}")

            # 5. 그룹 가입 및 연결 수락
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
            
            print(f"[SUCCESS] ✅ WebSocket 연결 성공: {self.username} → {room_name} ({self.room_uuid})")
            
            # 6. 입장 메시지 전송
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_joined",
                    "username": self.username,
                    "message": f"{self.username}님이 입장했습니다.",
                    "timestamp": timezone.now().isoformat(),
                    "room_name": room_name,
                }
            )
            
        except Exception as e:
            print(f"[ERROR] WebSocket 연결 중 예외 발생: {e}")
            import traceback
            traceback.print_exc()
            await self.close(code=4000)

    async def disconnect(self, close_code):
        try:
            if hasattr(self, 'room_group_name') and hasattr(self, 'username'):
                # 퇴장 메시지 전송
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "user_left",
                        "username": self.username,
                        "message": f"{self.username}님이 퇴장했습니다.",
                        "timestamp": timezone.now().isoformat(),
                    }
                )
                
                # 그룹에서 제거
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
                
            print(f"[DEBUG] WebSocket 연결 종료: {getattr(self, 'username', 'Unknown')} (code: {close_code})")
            
        except Exception as e:
            print(f"[ERROR] WebSocket 연결 종료 중 오류: {e}")

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
            message_type = data.get("type", "message")
            
            if message_type == "message":
                await self._handle_chat_message(data)
            elif message_type == "typing":
                await self._handle_typing_indicator(data)
                
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON 파싱 실패: {e}")
        except Exception as e:
            print(f"[ERROR] 메시지 처리 실패: {e}")

    async def _handle_chat_message(self, data):
        """채팅 메시지 처리"""
        message = data.get("message", "").strip()
        if not message:
            return

        # 메시지 길이 제한
        if len(message) > 1000:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "메시지가 너무 깁니다. (최대 1000자)"
            }))
            return

        # 메시지 DB에 저장
        stored_message = await self._save_message(self.room, self.user_profile, message)
        
        # 그룹의 모든 사용자에게 메시지 전송
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "username": self.username,
                "message_id": stored_message.id,
                "created_at": stored_message.created_at.isoformat(),
                "sender_id": self.user_profile.id,
            }
        )

    async def _handle_typing_indicator(self, data):
        """타이핑 표시 처리"""
        is_typing = data.get("is_typing", False)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "typing_indicator",
                "username": self.username,
                "is_typing": is_typing,
            }
        )

    # WebSocket 이벤트 핸들러들
    async def chat_message(self, event):
        """채팅 메시지 전송"""
        await self.send(text_data=json.dumps({
            "type": "message",
            "message": event.get("message"),
            "username": event.get("username"),
            "message_id": event.get("message_id"),
            "created_at": event.get("created_at"),
            "sender_id": event.get("sender_id"),
        }))

    async def user_joined(self, event):
        """사용자 입장 알림"""
        await self.send(text_data=json.dumps({
            "type": "user_joined",
            "message": event.get("message"),
            "username": event.get("username"),
            "timestamp": event.get("timestamp"),
            "room_name": event.get("room_name"),
        }))

    async def user_left(self, event):
        """사용자 퇴장 알림"""
        await self.send(text_data=json.dumps({
            "type": "user_left", 
            "message": event.get("message"),
            "username": event.get("username"),
            "timestamp": event.get("timestamp"),
        }))

    async def typing_indicator(self, event):
        """타이핑 표시"""
        if event.get("username") != self.username:
            await self.send(text_data=json.dumps({
                "type": "typing",
                "username": event.get("username"),
                "is_typing": event.get("is_typing"),
            }))

    # 데이터베이스 접근 함수들 (모두 database_sync_to_async로 감싸기)
    @database_sync_to_async
    def _get_user_profile(self, user):
        """사용자 프로필 가져오기/생성"""
        try:
            profile, created = UserProfile.objects.get_or_create(user=user)
            if created:
                print(f"[DEBUG] 새 UserProfile 생성: {user.username}")
            print(f"[DEBUG] UserProfile 조회 성공: {user.username}")
            return profile
        except Exception as e:
            print(f"[ERROR] UserProfile 조회 실패: {e}")
            return None

    @database_sync_to_async
    def _get_room_and_check_permission(self, room_uuid: uuid.UUID, user_profile: UserProfile):
        """채팅방 존재 여부 및 참여 권한 확인 (UUID 기반) - 모든 관련 데이터를 한번에 가져오기"""
        try:
            print(f"[DEBUG] 방 조회 시작: {room_uuid}")
            
            # select_related로 관련 데이터를 한번에 가져옴
            room = ChatRoom.objects.select_related('admin__user').get(room_uuid=room_uuid)
            print(f"[DEBUG] 방 조회 성공: {room.room_name}")
            
            # 참여 권한 확인: 방장이거나 참가자여야 함
            is_admin = room.admin == user_profile
            is_participant = user_profile in room.participants.all()
            
            print(f"[DEBUG] 권한 확인 - 방장: {is_admin}, 참가자: {is_participant}")
            
            if is_admin or is_participant:
                print(f"[DEBUG] ✅ 권한 확인 완료: {user_profile.user.username} → {room.room_name}")
                
                # async 컨텍스트에서 안전하게 사용할 수 있도록 필요한 데이터만 반환
                return {
                    'room': room,
                    'room_name': room.room_name,
                    'admin_username': room.admin.user.username,
                    'is_admin': is_admin,
                    'is_participant': is_participant
                }
            else:
                print(f"[DEBUG] ❌ 참여 권한 없음: {user_profile.user.username} → {room.room_name}")
                return None
                
        except ChatRoom.DoesNotExist:
            print(f"[DEBUG] ❌ 방이 존재하지 않음: {room_uuid}")
            return None
        except Exception as e:
            print(f"[ERROR] 방 조회 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return None

    @database_sync_to_async
    def _save_message(self, room: ChatRoom, sender: UserProfile, content: str):
        """메시지 DB에 저장"""
        try:
            message = Message.objects.create(
                room=room, 
                sender=sender, 
                content=content,
                created_at=timezone.now()
            )
            print(f"[DEBUG] 메시지 저장: {sender.user.username} → {content[:50]}...")
            return message
        except Exception as e:
            print(f"[ERROR] 메시지 저장 실패: {e}")
            return None