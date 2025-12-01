import pyotp
from .crypto_utils import encrypt_aes_gcm, generate_pseudo_number
from .models import ChatRoom
from login.models import UserProfile
from login.auth_check import check_authentication
from .room_utils import load_room_name, save_room_secret_key, get_room_secret
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseServerError
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from django.contrib.auth.models import User
import redis
from datetime import timedelta

# Redis 설정
redis_client = redis.Redis(host="localhost", port=6379, db=0)

# Create your views here.
@require_GET
@login_required
def get_my_rooms(request):
    """사용자가 참여한 모든 방 목록 반환"""
    try:
        auth_error = check_authentication(request)
        if auth_error:
            return auth_error
        
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return JsonResponse({"rooms": [], "total_count": 0})
        
        # 방장인 방 + 참가자인 방
        admin_rooms = ChatRoom.objects.filter(admin=user_profile)
        participant_rooms = ChatRoom.objects.filter(participants=user_profile)
        all_rooms = (admin_rooms | participant_rooms).distinct().order_by('-updated_at')
        
        rooms_data = []
        for room in all_rooms:
            room_info = {
                "id": str(room.room_uuid),  # 프론트가 이걸로 방 식별
                "name": room.room_name,
                "description": room.description,
                "admin": room.admin.username,
                "is_admin": (room.admin == user_profile),
                "participant_count": room.participants.count() + 1,
                "last_activity": room.updated_at.isoformat(),
                "created_at": room.created_at.isoformat()
            }
            rooms_data.append(room_info)
        
        return JsonResponse({
            "result": "success",
            "rooms": rooms_data,
            "total_count": len(rooms_data)
        })
        
    except Exception as e:
        return JsonResponse({"error": f"Failed to get rooms: {str(e)}"}, status=500)



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


@csrf_exempt
@require_POST
@login_required
def delete_room(request):
    """
    방 나가기 함수
    - 방장이 나가면: 방 완전 삭제 (DB에서 제거)  
    - 참가자가 나가면: 해당 사용자만 참가자 목록에서 제거
    """
    try:
        print(f"[DEBUG] leave_room 시작 - User: {request.user.username}")
        
        # 인증 체크
        auth_error = check_authentication(request)
        if auth_error:
            return auth_error
        
        # 요청 데이터 파싱
        try:
            data = json.loads(request.body)
            room_uuid = data.get('room_uuid')
            print(f"[DEBUG] 나가기 요청 방 UUID: {room_uuid}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        
        if not room_uuid:
            return JsonResponse({"error": "Room UUID is required"}, status=400)
        
        # 현재 사용자 프로필 가져오기
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return JsonResponse({"error": "User profile not found"}, status=404)
        
        # 채팅방 존재 확인
        try:
            room = ChatRoom.objects.get(room_uuid=room_uuid)
            print(f"[DEBUG] 대상 방: {room.room_name}")
        except ChatRoom.DoesNotExist:
            return JsonResponse({"error": "Room not found"}, status=404)
        
        # 사용자가 방에 속해있는지 확인
        is_admin = (room.admin == user_profile)
        is_participant = user_profile in room.participants.all()
        
        if not (is_admin or is_participant):
            return JsonResponse({
                "error": "Access denied", 
                "message": "You are not a member of this room"
            }, status=403)
        
        # === 케이스 1: 방장이 나가는 경우 - 방 완전 삭제 ===
        if is_admin:
            print(f"[DEBUG] 방장이 나가기 - 방 완전 삭제 시작")
            
            # 삭제 전 정보 저장
            room_name = room.room_name
            participant_count = room.participants.count()
            
            print(f"[DEBUG] 삭제할 방 정보 - 이름: {room_name}, 참가자: {participant_count}명")
            
            # 1. SecureData 삭제 (채팅방 시크릿 키)
            try:
                from .models import SecureData
                secure_data = SecureData.objects.filter(room=room)
                secure_data_count = secure_data.count()
                secure_data.delete()
                print(f"[DEBUG] SecureData 삭제 완료: {secure_data_count}개")
            except Exception as e:
                print(f"[WARNING] SecureData 삭제 중 오류: {e}")
            
            # 2. Redis에서 관련 TOTP 캐시 삭제 (가능한 경우)
            try:
                # 현재 활성화된 TOTP가 있다면 삭제
                secret = get_room_secret(room.room_uuid)
                if secret:
                    totp = pyotp.TOTP(secret)
                    current_totp = totp.now()
                    redis_key = f"totp:{current_totp}"
                    redis_client.delete(redis_key)
                    print(f"[DEBUG] Redis TOTP 캐시 삭제: {redis_key}")
            except Exception as e:
                print(f"[WARNING] Redis 캐시 삭제 중 오류: {e}")
            
            # 3. 참가자 관계 해제 (ManyToMany 관계)
            try:
                room.participants.clear()
                print(f"[DEBUG] 참가자 관계 해제 완료")
            except Exception as e:
                print(f"[WARNING] 참가자 관계 해제 중 오류: {e}")
            
            # 4. 메시지 삭제 (Message 모델이 있다면)
            try:
                # messages = room.messages.all()
                # message_count = messages.count()
                # messages.delete()
                # print(f"[DEBUG] 메시지 삭제 완료: {message_count}개")
                pass
            except Exception as e:
                print(f"[WARNING] 메시지 삭제 중 오류: {e}")
            
            # 5. 현재 세션에서 선택된 방이 삭제되는 방이라면 세션 정리
            if request.session.get('selected_room_uuid') == room_uuid:
                del request.session['selected_room_uuid']
                print(f"[DEBUG] 세션에서 선택된 방 정보 삭제")
            
            # 6. 마지막으로 채팅방 완전 삭제
            room.delete()
            print(f"[DEBUG] 채팅방 '{room_name}' 완전 삭제 완료")
            
            return JsonResponse({
                "result": "room_deleted",
                "message": f"Room '{room_name}' has been permanently deleted",
                "action": "room_deleted",
                "deleted_room": {
                    "uuid": room_uuid,
                    "name": room_name,
                    "participant_count": participant_count
                }
            })
        
        # === 케이스 2: 참가자가 나가는 경우 - 참가자 목록에서만 제거 ===
        else:
            print(f"[DEBUG] 참가자가 나가기 - 참가자 목록에서만 제거")
            
            # 참가자 목록에서 해당 사용자 제거
            room.participants.remove(user_profile)
            
            # 방 활동 시간 업데이트
            from django.utils import timezone
            room.updated_at = timezone.now()
            room.save()
            
            # 현재 세션에서 선택된 방이 나간 방이라면 세션 정리
            if request.session.get('selected_room_uuid') == room_uuid:
                del request.session['selected_room_uuid']
                print(f"[DEBUG] 세션에서 선택된 방 정보 삭제")
            
            remaining_participants = room.participants.count()
            print(f"[DEBUG] 사용자 {user_profile.username}가 {room.room_name}에서 나감. 남은 참가자: {remaining_participants}명")
            
            return JsonResponse({
                "result": "left_room",
                "message": f"You have left the room '{room.room_name}'",
                "action": "left_room", 
                "room": {
                    "uuid": str(room.room_uuid),
                    "name": room.room_name,
                    "remaining_participants": remaining_participants + 1  # +1은 방장
                }
            })
        
    except Exception as e:
        print(f"[ERROR] leave_room 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "error": "Failed to leave room",
            "message": "An unexpected error occurred while leaving the room"
        }, status=500)

@csrf_exempt
@require_POST
@login_required
def generate_totp(request):
    """POST로 UUID를 받아서 TOTP 생성 - 방장만 가능"""
    try:
        print("[DEBUG] generate_totp 시작")
        
        auth_error = check_authentication(request)
        if auth_error:
            return auth_error
        
        # POST body에서 room_uuid 추출
        try:
            data = json.loads(request.body)
            room_uuid = data.get('room_uuid')
            print(f"[DEBUG] 요청된 room_uuid: {room_uuid}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        
        if not room_uuid:
            return JsonResponse({"error": "Room UUID is required"}, status=400)
        
        # 사용자 프로필 가져오기
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return JsonResponse({"error": "User profile not found"}, status=404)
        
        # 방 존재 확인
        try:
            room = ChatRoom.objects.get(room_uuid=room_uuid)
            print(f"[DEBUG] 방 찾음: {room.room_name}")
        except ChatRoom.DoesNotExist:
            return JsonResponse({"error": "Room not found"}, status=404)
        
        # 방장 권한 확인
        if room.admin != user_profile:
            return JsonResponse({
                "error": "Permission denied",
                "message": "Only admin can generate TOTP"
            }, status=403)
        
        # TOTP 생성
        secret = get_room_secret(room.room_uuid)
        if not secret:
            return JsonResponse({"error": "Room secret not found"}, status=404)
        
        totp = pyotp.TOTP(secret)
        current_totp = totp.now()
        print(f"[DEBUG] 생성된 TOTP: {current_totp}")
        
        # Redis에 TOTP -> Room UUID 매핑 저장 (30초 TTL)
        redis_key = f"totp:{current_totp}"
        redis_value = {
            "room_uuid": str(room.room_uuid),
            "room_name": room.room_name,
            "admin": room.admin.username
        }
        redis_client.setex(redis_key, 30, json.dumps(redis_value))
        print(f"[DEBUG] Redis 저장 완료: {redis_key}")

        return JsonResponse({
            "result": "success",
            "totp": current_totp,
            "interval": 30,
            "room_name": room.room_name,
            "room_uuid": str(room.room_uuid)
        })
        
    except Exception as e:
        print(f"[ERROR] generate_totp 예외: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "error": "Failed to generate TOTP",
            "message": str(e)
        }, status=500)
      
@csrf_exempt
@require_POST
@login_required
def join_room(request):
    """TOTP 코드만으로 방 참여 - UUID 불필요"""
    try:
        print(f"[DEBUG] join_room_by_totp 시작 - User: {request.user.username}")
        
        # 인증 체크
        auth_error = check_authentication(request)
        if auth_error:
            return auth_error
        
        # 요청 데이터 파싱
        try:
            data = json.loads(request.body)
            totp_code = data.get('totp')
            print(f"[DEBUG] 입력된 TOTP: {totp_code}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        
        if not totp_code:
            return JsonResponse({"error": "TOTP code is required"}, status=400)
        
        # TOTP 6자리인지 검증
        if not (totp_code.isdigit() and len(totp_code) == 6):
            return JsonResponse({"error": "Invalid TOTP format. Must be 6 digits."}, status=400)
        
        # 현재 사용자 프로필 가져오기
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            user_profile = UserProfile.objects.create(user=request.user)
        
        print(f"[DEBUG] 사용자 프로필: {user_profile.username}")

        # Redis에서 빠르게 검색
        redis_key = f"totp:{totp_code}"
        room_data = redis_client.get(redis_key)

        if not room_data:
            return JsonResponse({"error": "Invalid or expired TOTP"}, status=400)

        # Redis에서 방 정보 추출
        try:
            room_info = json.loads(room_data)
            room_uuid_from_cache = room_info['room_uuid']
            room_name_from_cache = room_info['room_name']
        except (json.JSONDecodeError, KeyError) as e:
            return JsonResponse({"error": "Invalid cached room data"}, status=500)
        
        # 해당 방 가져오기
        try:
            room = ChatRoom.objects.get(room_uuid=room_uuid_from_cache)
        except ChatRoom.DoesNotExist:
            redis_client.delete(redis_key)
            return JsonResponse({"error": "Room no longer exists"}, status=404)
        
        # 이미 참여 중인지 확인
        if user_profile in room.participants.all() or room.admin == user_profile:
            print(f"[DEBUG] 사용자 이미 참여 중: {user_profile.username}")
            return JsonResponse({
                "result": "already_joined",
                "message": "You are already a participant in this room",
                "room_uuid": str(room.room_uuid),
                "room_name": room.room_name,
                "admin": room.admin.username
            })
        
        # 방에 참여 추가
        room.participants.add(user_profile)
        print(f"[DEBUG] 사용자 {user_profile.username}를 {room.room_name}에 추가 완료")
        
        # 방 활동 시간 업데이트 (선택사항)
        from django.utils import timezone
        room.updated_at = timezone.now()
        room.save()
        
        return JsonResponse({
            "result": "success",
            "message": "Successfully joined the room",
            "room_uuid": str(room.room_uuid),
            "room_name": room.room_name,
            "participant_count": room.participants.count(),
            "admin": room.admin.username,
            "user_role": "participant"
        })
        
    except Exception as e:
        print(f"[ERROR] join_room 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "error": "Failed to join room",
            "message": "An unexpected error occurred"
        }, status=500)

@csrf_exempt
@require_POST
@login_required
def select_room(request):
    """방 목록에서 방을 선택했을 때 서버 세션에 저장"""
    try:
        auth_error = check_authentication(request)
        if auth_error:
            return auth_error
        
        data = json.loads(request.body)
        room_uuid = data.get('room_uuid')  # 방 목록에서 받은 ID (UUID)
        
        if not room_uuid:
            return JsonResponse({"error": "Room ID is required"}, status=400)
        
        # 권한 확인
        user_profile = UserProfile.objects.get(user=request.user)
        try:
            room = ChatRoom.objects.get(room_uuid=room_uuid)
            
            is_admin = (room.admin == user_profile)
            is_participant = user_profile in room.participants.all()
            
            if not (is_admin or is_participant):
                return JsonResponse({"error": "Access denied"}, status=403)
            
            # 세션에 선택된 방 저장
            request.session['selected_room_uuid'] = room_uuid
            
            return JsonResponse({
                "result": "success",
                "message": "Room selected successfully"
            })
            
        except ChatRoom.DoesNotExist:
            return JsonResponse({"error": "Room not found"}, status=404)
        
    except Exception as e:
        return JsonResponse({"error": f"Failed to select room: {str(e)}"}, status=500)


@require_GET
@login_required
def get_current_room_info(request):
    """현재 선택된 방의 상세 정보 반환 - UUID 불필요"""
    try:
        auth_error = check_authentication(request)
        if auth_error:
            return auth_error
        
        # 세션에서 선택된 방 UUID 가져오기
        room_uuid = request.session.get('selected_room_uuid')
        if not room_uuid:
            return JsonResponse({"error": "No room selected"}, status=400)
        
        user_profile = UserProfile.objects.get(user=request.user)
        
        try:
            room = ChatRoom.objects.get(room_uuid=room_uuid)
        except ChatRoom.DoesNotExist:
            return JsonResponse({"error": "Selected room not found"}, status=404)
        
        # 권한 확인
        is_admin = (room.admin == user_profile)
        is_participant = user_profile in room.participants.all()
        
        if not (is_admin or is_participant):
            return JsonResponse({"error": "Access denied"}, status=403)
        
        # 참가자 목록
        participants = []
        participants.append({
            "username": room.admin.username,
            "role": "admin",
            "is_admin": True
        })
        
        for participant in room.participants.all():
            if participant != room.admin:
                participants.append({
                    "username": participant.username,
                    "role": "participant",
                    "is_admin": False
                })
        
        room_info = {
            "result": "success",
            "room": {
                "room_uuid": str(room.room_uuid),
                "room_name": room.room_name,
                "description": room.description,
                "admin": room.admin.username,
                "participant_count": len(participants),
                "participants": participants,
                "user_role": "admin" if is_admin else "participant",
                "can_generate_totp": is_admin,
                "created_at": room.created_at.isoformat(),
                "updated_at": room.updated_at.isoformat()
            }
        }
        
        return JsonResponse(room_info)
        
    except Exception as e:
        return JsonResponse({"error": f"Failed to get room info: {str(e)}"}, status=500)


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