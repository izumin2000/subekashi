web: gunicorn izuminapp.wsgi
release: python manage.py collectstatic --noinput
release: python manage.py migrate