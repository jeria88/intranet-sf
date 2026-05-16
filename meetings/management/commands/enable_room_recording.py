"""
Activa la grabación cloud automática en todas las salas Daily.co del sistema.

Llama PATCH /v1/rooms/{name} con enable_recording='cloud' para que Daily
inicie y detenga la grabación automáticamente sin intervención de la app.

Uso:
    python manage.py enable_room_recording
    python manage.py enable_room_recording --dry-run
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import requests
from meetings.models import MeetingRoom


class Command(BaseCommand):
    help = 'Activa enable_recording=cloud en todas las salas Daily del sistema'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Muestra qué haría sin ejecutar')

    def handle(self, *args, **options):
        api_key = (settings.DAILY_API_KEY or '').strip()
        if not api_key:
            self.stdout.write(self.style.ERROR('❌ DAILY_API_KEY no configurada'))
            return

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }

        rooms = MeetingRoom.objects.filter(room_type='daily').exclude(daily_identifier='')
        if not rooms.exists():
            self.stdout.write(self.style.WARNING('⚠️  No hay salas Daily registradas'))
            return

        self.stdout.write(f'🔍 {rooms.count()} sala(s) encontrada(s)\n')

        for room in rooms:
            name = room.daily_identifier
            if options['dry_run']:
                self.stdout.write(f'   [dry-run] PATCH /rooms/{name} → enable_recording=cloud')
                continue

            try:
                res = requests.patch(
                    f'https://api.daily.co/v1/rooms/{name}',
                    headers=headers,
                    json={'properties': {'enable_recording': 'cloud'}},
                    timeout=10,
                )
                if res.status_code == 200:
                    self.stdout.write(self.style.SUCCESS(f'   ✅ {name} — grabación cloud activada'))
                else:
                    self.stdout.write(self.style.ERROR(
                        f'   ❌ {name} — error {res.status_code}: {res.text[:120]}'
                    ))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ {name} — excepción: {e}'))
