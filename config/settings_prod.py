"""
Production settings — Railway.app
Hereda de settings.py y sobreescribe para producción.
Variables de entorno definidas en .env.example
"""
import os
import dj_database_url
from .settings import *  # noqa

# ── Seguridad ─────────────────────────────────────────────────────────────
SECRET_KEY = os.environ['SECRET_KEY']  # Obligatorio en producción
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

_raw_hosts = os.environ.get('ALLOWED_HOSTS', '*.railway.app')
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(',')]

CSRF_TRUSTED_ORIGINS = [
    f'https://{h}' for h in ALLOWED_HOSTS if not h.startswith('*')
] + [
    'https://*.railway.app',
]

# ── Base de Datos — PostgreSQL Railway ────────────────────────────────────
# Railway inyecta DATABASE_URL automáticamente al agregar el plugin PostgreSQL
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', ''),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ── Archivos estáticos — WhiteNoise ───────────────────────────────────────
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Seguridad HTTPS ───────────────────────────────────────────────────────
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ── Logging en producción ─────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
