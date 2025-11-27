from django.http import JsonResponse

def check_authentication(request):
    """인증 체크 함수"""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None