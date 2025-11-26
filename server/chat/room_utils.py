import json
from django.db import IntegrityError, transaction
from django.http import (
    JsonResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
    HttpResponseServerError,
)
from django.shortcuts import get_object_or_404

from .models import SecureData, ChatRoom
from .crypto_utils import decrypt_aes_gcm


def load_room_name(request):
    """
    POST 요청에서 room_name을 꺼내는 유틸 함수.
    - JSON: {"room_name": "..."}
    - form-data / x-www-form-urlencoded: room_name 필드
    """
    try:
        if request.content_type == "application/json":
            payload = json.loads(request.body.decode("utf-8") or "{}")
            room_name = payload.get("room_name")
        else:
            room_name = request.POST.get("room_name")
    except Exception:
        return HttpResponseBadRequest("invalid request body")

    if not room_name or not isinstance(room_name, str):
        return HttpResponseBadRequest("missing or invalid 'room_name'")

    room_name = room_name.strip()[:50]
    return room_name

#테이블에 암호문 저장
def save_room_secret_key(room_name: str, encrypted: str, admin_profile):
    """
    ChatRoom, SecureData를 트랜잭션으로 함께 저장.
    - encrypted: base64(iv + ciphertext) 문자열
    - 성공 시: ChatRoom 인스턴스 반환
    - 실패 시: HttpResponse(400/500) 반환
    """
    try:
        with transaction.atomic():
            room = ChatRoom.objects.create(
                room_name=room_name,
                admin=admin_profile
            )
            room.participants.add(admin_profile)

            secure = SecureData.objects.create(
                room=room,
                encrypted_value=encrypted,  # base64(iv + ciphertext)
            )
            # 디버그용 로그 (원하면 삭제해도 됨)
            print(f"[DEBUG] Created ChatRoom(room_id={room.room_id}) "
                  f"and SecureData(id={secure.id})")
    except IntegrityError:
        return HttpResponseBadRequest("room_name already exists")
    except Exception as e:
        print("[ERROR] save_room_secret_key:", e)
        return HttpResponseServerError("failed to save room and secret")

    return room


#totp 코드 필요할 때 암호문 가져와서 복호화
def get_room_secret(room_id):
    """
    room_id로 ChatRoom과 SecureData를 찾고,
    AES-GCM 복호화 후 TOTP용 base32 문자열 반환.
    복호화 실패/데이터 없음 → None
    """
    room = get_object_or_404(ChatRoom, room_id=room_id)
    secure = (
        SecureData.objects
        .filter(room=room)
        .order_by("-created_at")
        .first()
    )
    if not secure:
        print(f"[DEBUG] No SecureData for room_id={room_id}")
        return None

    try:
        secret_bytes = decrypt_aes_gcm(secure.encrypted_value)
        # generate_pseudo_number에서 ascii로 만들었으므로 ascii decode
        secret = secret_bytes.decode("ascii")
        return secret
    except Exception as e:
        print("[ERROR] get_room_secret:", e)
        return None