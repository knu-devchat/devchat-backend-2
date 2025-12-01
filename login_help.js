// ========================================
// 강제 로그인 스크립트 (개발용)
// ========================================
console.log('🔐 테스트용 로그인 시도...\n');

// Django 관리자 페이지를 통해 로그인
async function devLogin() {
    console.log('📋 방법 1: GitHub OAuth 로그인 (권장)');
    console.log('   👉 http://127.0.0.1:8000/login/github/ 로 이동하세요.\n');
    
    console.log('📋 방법 2: Django Admin 로그인');
    console.log('   1. http://127.0.0.1:8000/admin/ 접속');
    console.log('   2. superuser 계정으로 로그인');
    console.log('   3. 다시 이 페이지로 돌아와서 테스트\n');
    
    console.log('📋 방법 3: 컨테이너에서 직접 세션 생성');
    console.log('   docker-compose exec web python manage.py shell');
    console.log('   >>> from django.contrib.auth.models import User');
    console.log('   >>> from django.contrib.sessions.models import Session');
    console.log('   >>> from django.contrib.sessions.backends.db import SessionStore');
    console.log('   >>> user = User.objects.get(username="testuser")');
    console.log('   >>> session = SessionStore()');
    console.log('   >>> session["_auth_user_id"] = str(user.pk)');
    console.log('   >>> session.save()');
    console.log('   >>> print("sessionid:", session.session_key)');
}

devLogin();

// 또는 간단하게 GitHub 로그인 페이지로 이동
console.log('\n💡 GitHub 로그인 페이지로 이동하려면:');
console.log('window.location.href = "http://127.0.0.1:8000/login/github/"');
