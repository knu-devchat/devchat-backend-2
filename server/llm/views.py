import uuid
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import AiChatSession
from chat.models import ChatRoom # ChatRoom 모델 임포트

@require_POST
@login_required
def start_ai_session(request):
    # 🚨 주의: ChatRoom ID를 요청 바디에서 받아야 합니다.
    # 예시를 단순화하기 위해 room_id=1번으로 가정합니다.
    try:
        base_room = ChatRoom.objects.get(room_id=1) 
    except ChatRoom.DoesNotExist:
        return JsonResponse({"error": "Base chat room not found"}, status=404)

    # 고유한 세션 ID 생성
    new_session_id = str(uuid.uuid4())
    
    # 객체 생성 및 DB 저장
    session = AiChatSession.objects.create(
        base_room=base_room,
        session_id=new_session_id
    )

    return JsonResponse({
        "session_id": new_session_id,
        "base_room_name": base_room.room_name
    }, status=201)