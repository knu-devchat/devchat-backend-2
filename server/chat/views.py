import pyotp
from .crypto_utils import encrypt_aes_gcm, generate_pseudo_number
from .models import ChatRoom
from login.models import UserProfile
from .room_utils import load_room_name, save_room_secret_key, get_room_secret
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseServerError
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from django.contrib.auth.models import User


# Create your views here.
@csrf_exempt
@require_POST
def create_chat_room(request):
    """채팅방 생성해서 room_id 반환"""
    try:
        # 0. 익명 사용자 거부
        if not request.user.is_authenticated: 
            return JsonResponse({"error": "Authentication required"}, status=401)

        # 0. 현재 사용자 프로필 가져오기
        try:
            admin_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            admin_profile = UserProfile.objects.create(user=request.user)

        # 1. 채팅방 이름 전달
        room_name = load_room_name(request)
        if hasattr(room_name, "status_code"):
            return room_name

        # 2. 의사 난수 생성
        secret_key, iv = generate_pseudo_number()

        # 3. 채팅방 고유 비밀키 암호화
        encrypted = encrypt_aes_gcm(secret_key, iv)

        # 4. 채팅방 고유 비밀키 DB에 저장
        room_or_resp = save_room_secret_key(room_name, encrypted, admin_profile)
        if hasattr(room_or_resp, "status_code"):
            return room_or_resp

        # 성공: room_or_resp는 ChatRoom 인스턴스
        room = room_or_resp

        response = {
            "room_id": room.room_id,
            "room_name": room.room_name,
            "admin": admin_profile.username,
            "status": "success"
        }
        
        return JsonResponse(response)
    
    except Exception:
        return JsonResponse({
            "error": "Failed to create chat room"
        }, status=500)


@require_GET
@login_required
def generate_TOTP(request, room_id):
    """totp 6자리 숫자 반환"""

    # 1. 채팅방 존재 확인
    room = get_object_or_404(ChatRoom, room_id=room_id)

    # 2. 현재 사용자 프로필 가져오기
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return HttpResponseBadRequest("User profile not found")
    
    # 3. 권한 확인: 방장이거나 참여자여야 함
    if room.admin != user_profile and user_profile not in room.participants.all():
        return JsonResponse({"error": "You are not authorized to access this room"}, status=403)

    # 4. DB에서 채팅방 비밀키 가져와서 복호화
    secret = get_room_secret(room_id)
    if secret is None:
        return HttpResponseNotFound("secret not found")
    
    # 5. 복호화된 비밀키로 TOTP 생성
    totp = pyotp.TOTP(secret)
    code = totp.now()

    return JsonResponse({
        "totp": code,
        "interval": totp.interval,
        "room_name": room.room_name,
        "room_id": room.room_id
    })

@require_POST
@login_required
def join_room(request):
    """사용자가 totp 인증을 통해 방에 참여"""
    # req: totp(123456)
    # res: result(success), room_id(12)
    # res: error(nvalid_totp)
    pass

@require_GET
@login_required
def enter_room(request):
    """이미 참여한 방은 인증 없이 입장"""
    # res: result(entered), room_id(12)
    pass

@require_GET
@login_required
def list_messages(request, room_name):
    """채팅방 이름으로 최근 메시지를 조회"""
    # room = get_object_or_404(ChatRoom, room_name=room_name)
    # messages = room.messages.all()

    # payload = [
    #     {
    #         "id": message.id,
    #         "username": message.username,
    #         "content": message.content,
    #         "created_at": message.created_at.isoformat(),
    #     }
    #     for message in messages
    # ]

    # return JsonResponse({"messages": payload})