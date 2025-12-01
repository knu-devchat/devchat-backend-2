import uuid
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .models import AiChatSession, AiChatMessage
from chat.models import ChatRoom
from login.models import UserProfile

@csrf_exempt
@require_POST
@login_required
def start_ai_session(request):
    """AI 채팅 세션 시작"""
    try:
        print(f"\n[AI_API] ========== AI 세션 생성 요청 ==========")
        print(f"[AI_API] 사용자: {request.user.username}")
        
        # 0. 익명 사용자 거부
        if not request.user.is_authenticated:
            print(f"[AI_API ERROR] 인증되지 않은 사용자")
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        # 1. 요청 바디에서 room_uuid 또는 room_name 받기
        try:
            data = json.loads(request.body)
            room_uuid = data.get('room_uuid')
            room_name = data.get('room_name')
            
            print(f"[AI_API] 요청 데이터 - room_uuid: {room_uuid}, room_name: {room_name}")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"[AI_API ERROR] JSON 파싱 실패: {e}")
            return JsonResponse({"error": "Invalid request body"}, status=400)
        
        # 2. 사용자 프로필 가져오기
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            print(f"[AI_API ERROR] UserProfile이 존재하지 않음")
            return JsonResponse({"error": "User profile not found"}, status=404)
        
        # 3. ChatRoom 조회
        try:
            if room_uuid:
                base_room = ChatRoom.objects.get(room_uuid=room_uuid)
            elif room_name:
                base_room = ChatRoom.objects.get(room_name=room_name)
            else:
                print(f"[AI_API ERROR] room_uuid 또는 room_name이 필요함")
                return JsonResponse({"error": "room_uuid or room_name required"}, status=400)
            
            print(f"[AI_API] 채팅방 조회 성공: {base_room.room_name}")
        except ChatRoom.DoesNotExist:
            print(f"[AI_API ERROR] 채팅방을 찾을 수 없음")
            return JsonResponse({"error": "Chat room not found"}, status=404)
        
        # 4. 권한 확인: 방장이거나 참가자여야 함
        is_admin = base_room.admin == user_profile
        is_participant = user_profile in base_room.participants.all()
        
        if not (is_admin or is_participant):
            print(f"[AI_API ERROR] 채팅방 참여 권한 없음")
            return JsonResponse({"error": "No permission to access this room"}, status=403)
        
        print(f"[AI_API] 권한 확인 완료 - 방장: {is_admin}, 참가자: {is_participant}")

        # 5. 기존 활성 세션 확인 (방별로 하나의 활성 세션만 유지)
        existing_session = AiChatSession.objects.filter(
            base_room=base_room,
            is_active=True
        ).first()
        
        if existing_session:
            print(f"[AI_API] 🔄 기존 활성 세션 재사용: {existing_session.session_id}")
            session_id = existing_session.session_id
            message = "기존 AI 세션에 연결되었습니다."
            status_code = 200
        else:
            # 6. 새로운 세션 생성
            new_session_id = str(uuid.uuid4())
            session = AiChatSession.objects.create(
                base_room=base_room,
                session_id=new_session_id,
                is_active=True
            )
            print(f"[AI_API] ✨ 새 AI 세션 생성 완료: {new_session_id}")
            session_id = new_session_id
            message = "새로운 AI 세션이 생성되었습니다."
            status_code = 201

        return JsonResponse({
            "result": "success",
            "session_id": session_id,
            "room_uuid": str(base_room.room_uuid),
            "room_name": base_room.room_name,
            "message": message
        }, status=status_code)
        
    except Exception as e:
        print(f"[AI_API ERROR] AI 세션 생성 중 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": f"Failed to create AI session: {str(e)}"}, status=500)


@require_GET
@login_required
def get_ai_sessions(request):
    """사용자의 활성 AI 세션 목록 조회"""
    try:
        print(f"\n[AI_API] ========== AI 세션 목록 조회 ==========")
        print(f"[AI_API] 사용자: {request.user.username}")
        
        # 사용자 프로필 가져오기
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return JsonResponse({"sessions": [], "total_count": 0})
        
        # 사용자가 참여한 방의 활성 AI 세션들 가져오기
        admin_rooms = ChatRoom.objects.filter(admin=user_profile)
        participant_rooms = ChatRoom.objects.filter(participants=user_profile)
        all_rooms = (admin_rooms | participant_rooms).distinct()
        
        active_sessions = AiChatSession.objects.filter(
            base_room__in=all_rooms,
            is_active=True
        ).select_related('base_room').order_by('-created_at')
        
        sessions_data = []
        for session in active_sessions:
            session_info = {
                "session_id": session.session_id,
                "room_uuid": str(session.base_room.room_uuid),
                "room_name": session.base_room.room_name,
                "created_at": session.created_at.isoformat(),
            }
            sessions_data.append(session_info)
        
        print(f"[AI_API] AI 세션 {len(sessions_data)}개 조회 완료")
        
        return JsonResponse({
            "result": "success",
            "sessions": sessions_data,
            "total_count": len(sessions_data)
        })
        
    except Exception as e:
        print(f"[AI_API ERROR] AI 세션 목록 조회 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": f"Failed to get AI sessions: {str(e)}"}, status=500)


@require_GET
@login_required
def get_ai_messages(request, session_id):
    """특정 AI 세션의 메시지 히스토리 조회"""
    try:
        print(f"\n[AI_API] ========== AI 메시지 조회 ==========\nsession_id: {session_id}")
        
        # 1. 사용자 프로필 검증
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return JsonResponse({"error": "User profile not found"}, status=404)
        
        # 2. AI 세션 조회 및 권한 확인
        try:
            session = AiChatSession.objects.select_related('base_room').get(
                session_id=session_id,
                is_active=True
            )
            
            # 권한 확인: 방장이거나 참가자여야 함
            room = session.base_room
            is_admin = room.admin == user_profile
            is_participant = user_profile in room.participants.all()
            
            if not (is_admin or is_participant):
                return JsonResponse({"error": "No permission to access this session"}, status=403)
                
        except AiChatSession.DoesNotExist:
            return JsonResponse({"error": "AI session not found"}, status=404)
        
        # 3. 페이지네이션 매개변수
        page = int(request.GET.get('page', 1))
        limit = min(int(request.GET.get('limit', 50)), 100)  # 최대 100개로 제한
        offset = (page - 1) * limit
        
        # 4. AI 메시지 조회 (전용 테이블에서)
        messages = AiChatMessage.objects.filter(
            session=session
        ).select_related(
            'sender__user'
        ).order_by('-created_at')[offset:offset + limit]
        
        total_count = AiChatMessage.objects.filter(session=session).count()
        
        # 5. 메시지 데이터 포맷팅
        messages_data = []
        for msg in messages:
            message_info = {
                "id": msg.id,
                "content": msg.content,
                "sender": {
                    "username": msg.sender.user.username,
                    "is_ai": msg.is_ai_message
                },
                "is_ai_message": msg.is_ai_message,
                "is_self": msg.sender == user_profile,
                "created_at": msg.created_at.isoformat(),
            }
            messages_data.append(message_info)
        
        # 6. 페이지네이션 정보
        total_pages = (total_count + limit - 1) // limit
        
        print(f"[AI_API] AI 메시지 {len(messages_data)}개 조회 완료")
        
        return JsonResponse({
            "result": "success",
            "messages": list(reversed(messages_data)),  # 오래된 순으로 정렬
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_messages": total_count,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        })
        
    except Exception as e:
        print(f"[AI_API ERROR] AI 메시지 조회 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": f"Failed to get AI messages: {str(e)}"}, status=500)