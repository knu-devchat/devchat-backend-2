# Python 3.11 slim 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Django 프로젝트 복사
COPY . .

# SQLite 데이터베이스를 위한 디렉터리 생성 및 권한 설정
RUN mkdir -p /app/server/db && chmod 755 /app/server/db

# 초기화 스크립트 생성 및 권한 설정
RUN echo '#!/bin/bash\n\
echo "=== Docker 컨테이너 초기화 시작 ==="\n\
cd /app/server\n\
\n\
echo "정적 파일 수집 중..."\n\
python manage.py collectstatic --noinput\n\
\n\
echo "마이그레이션 실행 중..."\n\
python manage.py migrate\n\
\n\
echo "관리자 계정 확인 중..."\n\
python manage.py shell -c "\
from django.contrib.auth.models import User; \
from django.contrib.sites.models import Site; \
from allauth.socialaccount.models import SocialApp; \
import os; \
\
# 관리자 계정 생성\
if not User.objects.filter(username='\''admin'\'').exists(): \
    User.objects.create_superuser('\''admin'\'', '\''admin@localhost'\'', '\''admin123'\''); \
    print('\''✅ 관리자 계정 생성 완료: admin/admin123'\''); \
else: \
    print('\''⏭️  관리자 계정이 이미 존재합니다'\''); \
\
# Site 도메인 설정\
site = Site.objects.get(pk=1); \
site.domain = '\''localhost:8000'\''; \
site.name = '\''DevChat Local'\''; \
site.save(); \
print(f'\''✅ Site 설정 완료: {site.domain}'\''); \
\
# GitHub OAuth 앱 등록\
github_client_id = os.environ.get('\''GITHUB_CLIENT_ID'\'', '\'''\''); \
github_client_secret = os.environ.get('\''GITHUB_CLIENT_SECRET'\'', '\'''\''); \
\
if github_client_id and github_client_secret: \
    social_app, created = SocialApp.objects.get_or_create( \
        provider='\''github'\'', \
        defaults={ \
            '\''name'\'': '\''GitHub'\'', \
            '\''client_id'\'': github_client_id, \
            '\''secret'\'': github_client_secret, \
        } \
    ); \
    social_app.sites.add(site); \
    if created: \
        print('\''✅ GitHub OAuth 앱 등록 완료'\''); \
    else: \
        print('\''⏭️  GitHub OAuth 앱이 이미 등록되어 있습니다'\''); \
else: \
    print('\''⚠️  GitHub OAuth 환경변수가 설정되지 않았습니다'\''); \
    print('\''   GITHUB_CLIENT_ID와 GITHUB_CLIENT_SECRET를 설정하세요'\''); \
"\n\
\n\
echo "테스트 데이터 생성 중..."\n\
python manage.py shell -c "\
from django.contrib.auth.models import User; \
from login.models import UserProfile; \
from chat.models import ChatRoom, SecureData; \
import pyotp; \
\
# 테스트 사용자 생성\
test_users = [ \
    {'\''username'\'': '\''testuser1'\'', '\''email'\'': '\''test1@example.com'\''}, \
    {'\''username'\'': '\''testuser2'\'', '\''email'\'': '\''test2@example.com'\''}, \
]; \
\
for user_data in test_users: \
    user, created = User.objects.get_or_create( \
        username=user_data['\''username'\''], \
        defaults={'\''email'\'': user_data['\''email'\'']} \
    ); \
    if created: \
        user.set_password('\''test123'\''); \
        user.save(); \
        profile, _ = UserProfile.objects.get_or_create( \
            user=user, \
            defaults={ \
                '\''github_username'\'': user_data['\''username'\''], \
                '\''profile_image'\'': f'\''https://via.placeholder.com/40x40?text={user_data[\"username\"][0]}'\'', \
            } \
        ); \
        print(f'\''✅ 테스트 사용자 생성: {user.username}'\''); \
\
# 테스트 채팅방 생성\
admin_profile = UserProfile.objects.first(); \
if admin_profile: \
    test_rooms = [ \
        {'\''name'\'': '\''General'\'', '\''description'\'': '\''일반 채팅방'\''}, \
        {'\''name'\'': '\''Development'\'', '\''description'\'': '\''개발 관련 채팅방'\''}, \
    ]; \
    for room_data in test_rooms: \
        room, created = ChatRoom.objects.get_or_create( \
            room_name=room_data['\''name'\''], \
            defaults={ \
                '\''description'\'': room_data['\''description'\''], \
                '\''admin'\'': admin_profile \
            } \
        ); \
        if created: \
            room.participants.set(UserProfile.objects.all()); \
            secret = pyotp.random_base32(); \
            SecureData.objects.create(room=room, encrypted_value=secret); \
            print(f'\''✅ 테스트 채팅방 생성: {room.room_name}'\''); \
\
print('\''🎉 모든 초기화 완료!'\''); \
"\n\
\n\
echo "=== 서버 시작 ==="\n\
python manage.py runserver 0.0.0.0:8000' > /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

# 환경변수 설정
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=server.settings
ENV PYTHONUNBUFFERED=1

# 포트 8000 노출
EXPOSE 8000

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/api/user/me/ || exit 1

# 초기화 스크립트 실행
CMD ["/app/docker-entrypoint.sh"]