web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn config.wsgi --workers 1 --timeout 120 --log-file -
