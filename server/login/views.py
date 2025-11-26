from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse

def home(request):
    return render(request, 'index.html')

def current_user(request):
    """현재 로그인된 사용자 정보 반환"""
    if request.user.is_authenticated:
        return JsonResponse({
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'is_authenticated': True,
        })
    else:
        return JsonResponse({'is_authenticated': False}, status=401)