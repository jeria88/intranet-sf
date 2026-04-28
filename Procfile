web: python manage.py migrate && python seed_railway.py && python manage.py setup_utp_temuco && python manage.py register_daily_webhook && gunicorn config.wsgi --workers 2 --timeout 120 --log-file -

