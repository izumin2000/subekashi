web: gunicorn config.wsgi
release: python manage.py collectstatic --noinput
release: python manage.py migrate