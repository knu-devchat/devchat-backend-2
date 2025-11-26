from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from .models import UserProfile

def home(request):
    return render(request, 'index.html')

def current_user(request):
    """현재 로그인된 사용자 정보 반환"""
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)

        return JsonResponse({
            # 기본 User 정보
            'id': request.user.id,
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
        })
    else:
        return JsonResponse({'is_authenticated': False}, status=401)