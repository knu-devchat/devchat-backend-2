# DevChat Backend Docker Setup

## 빠른 시작

### 개발 환경에서 실행

1. **환경변수 설정**
```bash
cp .env.docker .env
# .env 파일을 편집하여 실제 GitHub OAuth 정보 입력
```

2. **Docker 컨테이너 실행**
```bash
# 개발 모드 (Redis + Django)
docker-compose up -d

# 로그 확인
docker-compose logs -f web
```

3. **브라우저에서 접속**
- Django 애플리케이션: http://localhost:8000
- Django Admin: http://localhost:8000/admin/

### 프로덕션 환경에서 실행

```bash
# Nginx 포함하여 실행
docker-compose --profile production up -d

# HTTP 포트 80으로 접속
# http://localhost
```

## 서비스 구성

### 개발 모드
- `web`: Django 애플리케이션 (포트 8000)
- `redis`: Redis 서버 (포트 6379)

### 프로덕션 모드
- `web`: Django 애플리케이션
- `redis`: Redis 서버
- `nginx`: Nginx 리버스 프록시 (포트 80)

## 유용한 명령어

### 컨테이너 관리
```bash
# 컨테이너 시작
docker-compose up -d

# 컨테이너 중지
docker-compose down

# 컨테이너 재시작
docker-compose restart

# 로그 확인
docker-compose logs -f web
```

### Django 관리 명령
```bash
# Django 셸 접속
docker-compose exec web python server/manage.py shell

# 마이그레이션 생성
docker-compose exec web python server/manage.py makemigrations

# 마이그레이션 적용
docker-compose exec web python server/manage.py migrate

# 슈퍼유저 생성
docker-compose exec web python server/manage.py createsuperuser

# 정적 파일 수집
docker-compose exec web python server/manage.py collectstatic
```

### 데이터베이스 관리
```bash
# SQLite 데이터베이스 파일 확인
docker-compose exec web ls -la server/db/

# Django 데이터베이스 셸 접속
docker-compose exec web python server/manage.py dbshell

# Redis CLI 접속
docker-compose exec redis redis-cli

# 컨테이너 내부 접속
docker-compose exec web bash
```

## 환경변수 설정

`.env` 파일에서 다음 값들을 설정하세요:

### 필수 설정
- `DJANGO_SECRET_KEY`: Django 보안 키
- `CLIENT_ID`: GitHub OAuth Client ID
- `CLIENT_SECRET`: GitHub OAuth Client Secret
- `MASTER_KEY_B64`: 암호화용 마스터 키

### 선택적 설정
- `DEBUG`: 디버그 모드 (개발: True, 프로덕션: False)
- `ALLOWED_HOSTS`: 허용된 호스트 목록
- `CORS_ALLOWED_ORIGINS`: CORS 허용 오리진

## 볼륨 관리

### 데이터 백업
```bash
# SQLite 데이터베이스 백업
docker cp $(docker-compose ps -q web):/app/server/db/db.sqlite3 ./backup/

# Redis 데이터 백업
docker-compose exec redis redis-cli BGSAVE

# 정적 파일 백업
docker cp $(docker-compose ps -q web):/app/server/staticfiles ./backup/
```

### 볼륨 초기화
```bash
# 모든 볼륨 삭제 (주의: 데이터 손실)
docker-compose down -v
docker volume prune
```

## 문제 해결

### 컨테이너가 시작되지 않는 경우
```bash
# 로그 확인
docker-compose logs web

# 컨테이너 상태 확인
docker-compose ps

# 이미지 다시 빌드
docker-compose build --no-cache
```

### 데이터베이스 문제
```bash
# 마이그레이션 상태 확인
docker-compose exec web python server/manage.py showmigrations

# 마이그레이션 강제 적용
docker-compose exec web python server/manage.py migrate --fake
```

### Redis 연결 문제
```bash
# Redis 상태 확인
docker-compose exec redis redis-cli ping

# Redis 로그 확인
docker-compose logs redis
```

## 보안 주의사항

1. **프로덕션 환경에서는 반드시 실제 보안 키 사용**
2. **DEBUG=False로 설정**
3. **ALLOWED_HOSTS를 실제 도메인으로 제한**
4. **환경변수 파일을 Git에 커밋하지 마세요**