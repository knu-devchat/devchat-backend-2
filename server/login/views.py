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
    if not request.user.is_authenticated:
        return JsonResponse({'is_authenticated': False}, status=401)
    
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
                "room_uuid": str(room.pk),  # room_uuid가 primary_key
                "room_name": room.room_name,
                "description": room.description,
                "is_admin": room.admin == profile,
                "admin_username": room.admin.user.username,  # user.username → user.user.username
                "participant_count": room.participants.count() + 1,
                "created_at": room.created_at.isoformat(),
            })
            
    except Exception as e:
        print(f"[ERROR] getting rooms in current_user: {e}")
        rooms_data = []

    response_data = {
        # 기본 User 정보
        'uuid': str(profile.uuid) if hasattr(profile, 'uuid') else None,
        'username': request.user.username,
        'email': request.user.email,
        'is_authenticated': True,
        
        # UserProfile 추가 정보
        'avatar': profile.profile_image or '',  # avatar 필드 추가!
        'profile_image': profile.profile_image or '',
        'is_online': profile.is_online,
        'last_seen': profile.last_seen.isoformat() if profile.last_seen else None,
        
        # GitHub 정보
        'github_username': profile.github_username or '',
        'github_id': profile.github_id or '',
        'github_bio': profile.github_bio or '',
        'github_company': profile.github_company or '',
        'github_location': profile.github_location or '',
        'github_followers': profile.github_followers or 0,
        'github_following': profile.github_following or 0,
        
        # 채팅방 목록
        'rooms': rooms_data,
        'rooms_count': len(rooms_data)
    }
    
    return JsonResponse(response_data)

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