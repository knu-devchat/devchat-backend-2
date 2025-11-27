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
            body = request.body.decode('utf-8')
            if not body:
                return HttpResponseBadRequest("Empty request body")
            payload = json.loads(body)
            room_name = payload.get("room_name")
        else:
            room_name = request.POST.get("room_name")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON format")
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
            if ChatRoom.objects.filter(room_name=room_name).exists():
                return JsonResponse({"error": "Room name already exists"}, status=400)
            
            room = ChatRoom.objects.create(
                room_name=room_name,
                admin=admin_profile
            )
            room.participants.add(admin_profile)

            SecureData.objects.create(
                room=room,
                encrypted_value=encrypted,  # base64(iv + ciphertext)
            )
    except IntegrityError:
        return HttpResponseBadRequest("room_name already exists")
    except Exception as e:
        return HttpResponseServerError("failed to save room and secret")

    return room


#totp 코드 필요할 때 암호문 가져와서 복호화
def get_room_secret(room_uuid):
    try:
        from .models import ChatRoom, SecureData  # SecureData 모델 사용
        from .crypto_utils import decrypt_aes_gcm  # 복호화 함수
        
        # 1. 먼저 ChatRoom 객체 찾기
        room = ChatRoom.objects.get(room_uuid=room_uuid)
        
        # 2. room과 연결된 SecureData 찾기 (OneToOneField)
        secure_data = SecureData.objects.get(room=room)
        
        # 3. 복호화
        if secure_data.encrypted_value:
            decrypted_secret = decrypt_aes_gcm(secure_data.encrypted_value)
            return decrypted_secret
        else:
            return None
        
    except ChatRoom.DoesNotExist:
        return None
    except SecureData.DoesNotExist:
        return None
    except Exception as e:
        return None