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

# SQLite 데이터베이스를 위한 디렉터리 생성
RUN mkdir -p /app/server/db

# 환경변수 설정
ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=server.settings
ENV PYTHONUNBUFFERED=1

# 포트 8000 노출
EXPOSE 8000

# 정적 파일 수집 및 마이그레이션을 위한 스크립트
RUN echo '#!/bin/bash\n\
cd /app/server\n\
python manage.py collectstatic --noinput\n\
python manage.py migrate\n\
python manage.py runserver 0.0.0.0:8000' > /app/start.sh

RUN chmod +x /app/start.sh

# 컨테이너 시작시 실행할 명령
CMD ["/app/start.sh"]