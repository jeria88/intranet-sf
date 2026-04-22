"""
Management command para registrar el webhook de Daily.co.
Se ejecuta desde el servidor (con las credenciales correctas) sin depender de la validación de Daily.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import requests


class Command(BaseCommand):
    help = 'Registra el webhook de Daily.co para grabaciones'

    def handle(self, *args, **options):
        api_key = (settings.DAILY_API_KEY or '').strip()
        if not api_key:
            self.stdout.write(self.style.ERROR('DAILY_API_KEY no configurada'))
            return

        webhook_url = 'https://web-production-2b719.up.railway.app/salas/webhook/recording/'
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # 1. Limpiar webhooks existentes (solo 1 permitido por dominio)
        res = requests.get('https://api.daily.co/v1/webhooks', headers=headers)
        for w in res.json():
            requests.delete(f'https://api.daily.co/v1/webhooks/{w["uuid"]}', headers=headers)
            self.stdout.write(f'Eliminado webhook anterior: {w["uuid"]}')

        # 2. Registrar el nuevo webhook
        data = {'url': webhook_url}
        res = requests.post('https://api.daily.co/v1/webhooks', headers=headers, json=data)

        if res.status_code in [200, 201]:
            info = res.json()
            self.stdout.write(self.style.SUCCESS(
                f'✅ Webhook registrado exitosamente!\n'
                f'   UUID: {info.get("uuid")}\n'
                f'   URL: {info.get("url")}\n'
                f'   Estado: {info.get("state")}'
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f'❌ Error al registrar webhook: {res.status_code} - {res.text}'
            ))
