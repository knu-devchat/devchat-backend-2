FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then \
    pip install --no-cache-dir -r requirements.txt; \
    else \
    pip install --no-cache-dir \
        django==4.2.7 \
        djangorestframework==3.14.0 \
        django-cors-headers==4.3.1 \
        channels==4.0.0 \
        channels-redis==4.1.0 \
        redis==4.6.0 \
        cryptography==41.0.7 \
        requests==2.31.0 \
        django-allauth==0.57.0 \
        daphne==4.0.0 \
        psycopg2-binary==2.9.7; \
    fi

# 프로젝트 코드 복사
COPY server/ ./server/

WORKDIR /app/server

# SQLite 데이터베이스 디렉토리 생성 및 권한 설정
RUN mkdir -p /app/server/db && \
    chmod 755 /app/server/db && \
    touch /app/server/db.sqlite3 && \
    chmod 664 /app/server/db.sqlite3

EXPOSE 8000

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/admin/ || exit 1

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]