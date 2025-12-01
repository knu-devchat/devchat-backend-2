# 1. 프로젝트 루트 디렉토리에서 실행
docker-compose up --build

# 2. 백그라운드 실행
docker-compose up -d --build

# 3. 로그 확인
docker-compose logs -f web

# 4. Redis 접속 테스트
docker-compose exec redis redis-cli ping

# 5. Django 관리자 계정 생성
docker-compose exec web python manage.py createsuperuser

# 6. Django shell 접속
docker-compose exec web python manage.py shell