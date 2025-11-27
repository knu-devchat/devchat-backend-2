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
@require_GET
def get_user_rooms(request):
    """현재 사용자가 참여 중인 채팅방 목록 반환"""
    try:
        # 인증 체크
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        # 사용자 프로필 가져오기
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            user_profile = UserProfile.objects.create(user=request.user)

        # 방장인 방들
        admin_rooms = ChatRoom.objects.filter(admin=user_profile)

        # 참여자인 방들
        participant_rooms = ChatRoom.objects.filter(participants=user_profile)

        # 모든 방 통합
        all_rooms = (admin_rooms | participant_rooms).distinct().order_by('-created_at')

        rooms_data = []
        for room in all_rooms:
            rooms_data.append({
                "room_id": room.room_id,
                "room_uuid": str(room.room_uuid),
                "room_name": room.room_name,
                "description": room.description,
                "is_admin": room.admin == user_profile,
                "admin_username": room.admin.username,
                "participant_count": room.participants.count() + 1,  # +1은 방장 포함
                "created_at": room.created_at.isoformat(),
                # "last_message": None,  # 나중에 메시지 기능 구현 시 추가
                # "unread_count": 0,     # 나중에 읽음 상태 기능 구현 시 추가
            })

        return JsonResponse({
            "rooms": rooms_data,
            "total_count": len(rooms_data)
        })
        
    except Exception as e:
        print(f"[ERROR] get_user_rooms: {e}")
        return JsonResponse({
            "error": "Failed to get rooms",
            "message": "An unexpected error occurred"
        }, status=500)

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
            "room_uuid": str(room.room_uuid),
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
def generate_TOTP(request, room_uuid):
    """totp 6자리 숫자 반환 - 방장만 생성 가능"""
    try:
        # 인증 체크
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)

        # 1. UUID로 방 찾기
        try:
            room = ChatRoom.objects.get(room_uuid=room_uuid)
        except ChatRoom.DoesNotExist:
            return JsonResponse({"error": "Room not found"}, status=404)

        # 2. 현재 사용자 프로필 가져오기
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return JsonResponse({"error": "User profile not found"}, status=400)
        
        # 3. 권한 확인: 방장만 TOTP 생성 가능
        if room.admin != user_profile:
            return JsonResponse({"error": "Only room admin can generate TOTP"}, status=403)

        # 4. DB에서 채팅방 비밀키 가져와서 복호화
        secret = get_room_secret(room.room_id)
        if secret is None:
            return JsonResponse({"error": "Room secret not found"}, status=404)
        
        # 5. 복호화된 비밀키로 TOTP 생성
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        return JsonResponse({
            "totp": code,
            "interval": totp.interval,
            "room_name": room.room_name,
            "room_uuid": room.room_uuid,
        })
        
    except Exception as e:
        return JsonResponse({"error": "Failed to generate TOTP"}, status=500)

@require_POST
@login_required
def join_room(request, room_uuid):
    """사용자가 totp 인증을 통해 방에 참여"""
    # req: totp(123456)
    # res: result(success), room_id(12)
    # res: error(nvalid_totp)
    try:
        # 인증 체크
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        # 요청 데이터 파싱
        try:
            data = json.loads(request.body)
            totp_code = data.get('totp')
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        
        if not totp_code:
            return JsonResponse({"error": "TOTP code is required"}, status=400)
        
        # TOTP 6자리인지 검증
        if not (totp_code.isdigit() and len(totp_code)==6):
            return JsonResponse({"error": "Invalid TOTP format. Must be 6 digits."}, status=400)
        
        # 1. UUID로 방 찾기
        try:
            room = ChatRoom.objects.get(room_uuid=room_uuid)
        except ChatRoom.DoesNotExist:
            return JsonResponse({"error": "Room not found"}, status=404)
        
        # 2. 현재 사용자 프로필 가져오기
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            user_profile = UserProfile.objects.create(user=request.user)

        # 3. 이미 참여 중인지 확인
        if user_profile in room.participants.all() or room.admin == user_profile:
            return JsonResponse({
                "result": "already_joined",
                "message": "You are already a participant in this room",
                "room_uuid": str(room.room_uuid),
                "room_name": room.room_name
            })
        
        # 4. TOTP 코드 검증
        secret = get_room_secret(room.room_id)
        if secret is None:
            return JsonResponse({"error": "Room secret not found"}, status=404)
        
        totp = pyotp.TOTP(secret)
        # valid_window=1: 현재 시간 +-30초 범위에서 검증
        if not totp.verify(totp_code, valid_window=1):
            return JsonResponse({
                "error": "invalid_totp",
                "message": "Invalid or expired TOTP code"
            }, status=400)
        
        # 5. 방에 참여 추가
        room.participants.add(user_profile)

        return JsonResponse({
            "result": "success",
            "message": "Successfully joined the room",
            "room_uuid": str(room.room_uuid),
            "room_name": room.room_name,
            "participant_count": room.participants.count(),
            "admin": room.admin.username
        })
    
    except Exception as e:
        print(f"[ERROR] join_room: {e}")
        return JsonResponse({
            "error": "Failed to join room",
            "message": "An unexpected error occurred"
        }, status=500)

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