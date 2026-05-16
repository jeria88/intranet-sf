"""
Management command idempotente para garantizar que el webhook de Daily.co
esté registrado al arrancar la aplicación.

Comportamiento:
  - Si ya existe un webhook con la URL correcta → no hace nada (idempotente).
  - Si existe un webhook con URL diferente → lo elimina y registra el nuevo.
  - Si no existe ninguno → lo registra.

Uso en Procfile:
  python manage.py ensure_webhook && gunicorn ...
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import requests

WEBHOOK_URL = 'https://web-production-2b719.up.railway.app/salas/webhook/recording/'


class Command(BaseCommand):
    help = 'Registra el webhook de Daily.co si aún no está activo (idempotente)'

    def handle(self, *args, **options):
        api_key = (settings.DAILY_API_KEY or '').strip()
        if not api_key:
            self.stdout.write(self.style.WARNING(
                '⚠️  DAILY_API_KEY no configurada — se omite registro de webhook'
            ))
            return

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

        # ── 1. Verificar si ya existe el webhook correcto ──────────────────────
        try:
            res = requests.get('https://api.daily.co/v1/webhooks', headers=headers, timeout=10)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️  No se pudo contactar Daily.co: {e}'))
            return

        existing = res.json() if res.status_code == 200 else []

        for w in existing:
            if w.get('url') == WEBHOOK_URL and w.get('state') in ('enabled', 'active'):
                self.stdout.write(self.style.SUCCESS(
                    f'✅ Webhook ya registrado y activo (uuid={w["uuid"]}) — sin cambios'
                ))
                return

        # ── 2. Limpiar webhooks obsoletos ─────────────────────────────────────
        for w in existing:
            try:
                requests.delete(
                    f'https://api.daily.co/v1/webhooks/{w["uuid"]}',
                    headers=headers,
                    timeout=10,
                )
                self.stdout.write(f'   Eliminado webhook obsoleto: {w["uuid"]} ({w.get("url")})')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'   No se pudo eliminar webhook {w["uuid"]}: {e}'))

        # ── 3. Registrar nuevo webhook ─────────────────────────────────────────
        self.stdout.write(f'🔗 Registrando webhook → {WEBHOOK_URL}')
        try:
            res = requests.post(
                'https://api.daily.co/v1/webhooks',
                headers=headers,
                json={'url': WEBHOOK_URL},
                timeout=10,
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ No se pudo registrar webhook: {e}'))
            return

        if res.status_code in [200, 201]:
            info = res.json()
            self.stdout.write(self.style.SUCCESS(
                f'✅ Webhook registrado\n'
                f'   URL:   {info.get("url")}\n'
                f'   UUID:  {info.get("uuid")}\n'
                f'   Estado: {info.get("state")}'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f'❌ Error al registrar webhook: {res.status_code} — {res.text[:200]}'
            ))
