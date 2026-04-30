FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . /app

RUN pip install --upgrade pip setuptools wheel

RUN pip install --no-cache-dir -r requirements.txt

RUN cp config/local_settings_sample.py config/local_settings.py

RUN python -c "from django.core.management.utils import get_random_secret_key; \
key=get_random_secret_key(); \
path='config/local_settings.py'; \
txt=open(path).read(); \
txt=txt.replace('SECRET_KEY = \'\'', f'SECRET_KEY = \'{key}\''); \
open(path,'w').write(txt)"

RUN python manage.py makemigrations && \
    python manage.py migrate && \
    python manage.py loaddata data.json

RUN python manage.py const || true

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]