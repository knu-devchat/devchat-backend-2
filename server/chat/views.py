import pyotp
from .crypto_utils import encrypt_aes_gcm, generate_pseudo_number
from .models import ChatRoom, UserProfile
from .room_utils import load_room_name, save_room_secret_key, get_room_secret
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseServerError
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
import json


# Create your views here.
@csrf_exempt
@require_POST
def create_chat_room(request):
    """
    req: room_name 전달
    res:
        - DB ChatRoom에 room_id, room_name 저장
        - DB SecureData에 암호화된 채팅방 비밀키 저장
    """
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
    return JsonResponse({
        "room_id": room.room_id,
        "room_name": room.room_name,
        "admin": admin_profile.username
    })


@require_GET
def generate_TOTP(request, room_id):
    """
    req: 채팅방 생성 완료 -> 6자리 코드 필요
    res: 6자리 코드 반환
    """
    # 1. DB에서 비밀키 가져와서 복호화
    secret = get_room_secret(room_id)
    if secret is None:
        return HttpResponseNotFound("secret not found")
    
    # 2. 가져온 비밀키로 totp 생성, 6자리 코드 생성 -> 이 값을 api로 프론트에 내려줌
    totp = pyotp.TOTP(secret)
    code = totp.now()

    # 3. totp 프론트엔드로 반환
    return JsonResponse({"totp": code, "interval": totp.interval})

@require_POST
def join_room(request):
    """사용자가 totp 인증을 통해 방에 참여"""
    # req: totp(123456)
    # res: result(success), room_id(12)
    # res: error(nvalid_totp)
    pass

@require_GET
def enter_room(request):
    """이미 참여한 방은 인증 없이 입장"""
    # res: result(entered), room_id(12)
    pass

@require_GET
def list_messages(request, room_name):
    """
    채팅방 이름으로 최근 메시지를 조회
    """
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