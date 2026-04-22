"""
Management command para configurar Daily.co:
  1. Registrar el webhook (que luego auto-inicia las grabaciones via meeting-started)
  
La grabación automática se activa cuando Daily dispara 'meeting-started' al webhook,
y el webhook llama a POST /rooms/:name/recordings/start automáticamente.
No existe una propiedad de sala 'start_cloud_recording_on_start' en la API de Daily.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import requests

WEBHOOK_URL = 'https://web-production-2b719.up.railway.app/salas/webhook/recording/'


class Command(BaseCommand):
    help = 'Registra el webhook de Daily.co (que dispara grabación automática vía meeting-started)'

    def handle(self, *args, **options):
        api_key = (settings.DAILY_API_KEY or '').strip()
        if not api_key:
            self.stdout.write(self.style.ERROR('DAILY_API_KEY no configurada'))
            return

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # ── 1. Limpiar webhooks existentes (Daily solo permite 1 por dominio) ─
        self.stdout.write('🔗 Registrando webhook de Daily.co...')
        res = requests.get('https://api.daily.co/v1/webhooks', headers=headers)
        existing = res.json() if res.status_code == 200 else []
        for w in existing:
            requests.delete(f'https://api.daily.co/v1/webhooks/{w["uuid"]}', headers=headers)
            self.stdout.write(f'   Eliminado webhook anterior: {w["uuid"]}')

        # ── 2. Registrar el nuevo webhook ──────────────────────────────────────
        res = requests.post(
            'https://api.daily.co/v1/webhooks',
            headers=headers,
            json={'url': WEBHOOK_URL}
        )
        if res.status_code in [200, 201]:
            info = res.json()
            self.stdout.write(self.style.SUCCESS(
                f'✅ Webhook activo\n'
                f'   URL: {info.get("url")}\n'
                f'   UUID: {info.get("uuid")}\n'
                f'   Estado: {info.get("state")}\n\n'
                f'   ℹ️  La grabación automática se activará cuando Daily dispare\n'
                f'   el evento "meeting-started" al recibir el primer participante.'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f'❌ Error al registrar webhook: {res.status_code} - {res.text}'
            ))
