# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지
RUN apt-get update && apt-get install -y \
    git curl && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY requirements.txt .
RUN pip install -r requirements.txt

# 개발용 패키지 추가
RUN pip install django-cors-headers

COPY . .
WORKDIR /app/server

# 개발용 초기화
RUN echo '#!/bin/bash\n\
python manage.py makemigrations\n\
python manage.py migrate\n\
python manage.py shell -c "\
from django.contrib.auth.models import User;\
User.objects.get_or_create(username='\''admin'\'', defaults={'\''is_superuser'\'': True, '\''is_staff'\'': True});\
User.objects.filter(username='\''admin'\'').update(password='\''pbkdf2_sha256$600000$x$hash'\'');\
"\n\
exec "$@"' > /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]