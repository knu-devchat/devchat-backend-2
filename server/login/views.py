from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from .models import UserProfile
from django.views.decorators.http import require_POST, require_GET

def home(request):
    return render(request, 'index.html')

@require_GET
def current_user(request):
    """현재 로그인된 사용자 정보와 참여 중인 채팅방 목록 반환"""
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)

        # 채팅방 목록 가져오기
        try:
            from chat.models import ChatRoom
            
            # 방장인 방들
            admin_rooms = ChatRoom.objects.filter(admin=profile)
            
            # 참여자인 방들
            participant_rooms = ChatRoom.objects.filter(participants=profile)
            
            # 모든 방 통합 (중복 제거)
            all_rooms = (admin_rooms | participant_rooms).distinct().order_by('-created_at')
            
            rooms_data = []
            for room in all_rooms:
                rooms_data.append({
                    "room_id": room.room_id,
                    "room_uuid": str(room.room_uuid),
                    "room_name": room.room_name,
                    "description": room.description,
                    "is_admin": room.admin == profile,
                    "admin_username": room.admin.username,
                    "participant_count": room.participants.count() + 1,  # +1은 방장 포함
                    "created_at": room.created_at.isoformat(),
                })
                
        except Exception as e:
            print(f"[ERROR] getting rooms in current_user: {e}")
            rooms_data = []  # 에러 시 빈 배열

        return JsonResponse({
            # 기본 User 정보
            'uuid': str(profile.uuid) if hasattr(profile, 'uuid') else None,
            'username': request.user.username,
            'email': request.user.email,
            'is_authenticated': True,
            
            # UserProfile 추가 정보
            'profile_image': profile.profile_image,
            'is_online': profile.is_online,
            'last_seen': profile.last_seen,
            
            # GitHub 정보
            'github_username': profile.github_username,
            'github_id': profile.github_id,
            'github_bio': profile.github_bio,
            'github_company': profile.github_company,
            'github_location': profile.github_location,
            'github_followers': profile.github_followers,
            'github_following': profile.github_following,
            
            # 채팅방 목록 추가
            'rooms': rooms_data,
            'rooms_count': len(rooms_data)
        })
    else:
        return JsonResponse({'is_authenticated': False}, status=401)
    
@require_GET
def user_profile(request, user_uuid):
    """다른 사용자 프로필 조회 (UUID 사용)"""
    try:
        profile = UserProfile.objects.get(uuid=user_uuid)
        # 공개 정보만 반환
        return JsonResponse({
            'uuid': str(profile.uuid),
            'username': profile.user.username,
            'profile_image': profile.profile_image,
            'github_username': profile.github_username,
            'github_bio': profile.github_bio,
            'github_location': profile.github_location,
            # 민감한 정보는 제외
        })
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)