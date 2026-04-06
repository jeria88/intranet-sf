import os
import django
from django.utils import timezone
from datetime import timedelta

# Configurar entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from meetings.models import MeetingRoom, MeetingBooking
from ai_modules.models import AIAssistant

User = get_user_model()

print("🌱 Iniciando carga de datos iniciales...")

# ── Superusuario ─────────────────────────────────────────────────────────────
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@sfared.cl', 'admin123')
    print("✅ Superusuario 'admin' creado (pass: admin123)")
else:
    print("ℹ️  Superusuario 'admin' ya existe")

# ── Usuarios de demo (Consolidados en ANGOL para pruebas) ──────────────────
DEMO_USERS = [
    {'username': 'director.demo',     'first_name': 'Director',     'last_name': 'Demo',    'role': 'DIRECTOR',     'establishment': 'ANGOL',    'email': 'director@demo.cl'},
    {'username': 'utp.demo',          'first_name': 'UTP',          'last_name': 'Demo',    'role': 'UTP',          'establishment': 'ANGOL',    'email': 'utp@demo.cl'},
    {'username': 'inspector.demo',    'first_name': 'Inspector',    'last_name': 'Demo',    'role': 'INSPECTOR',    'establishment': 'ANGOL',    'email': 'inspector@demo.cl'},
    {'username': 'convivencia.demo', 'first_name': 'Convivencia', 'last_name': 'Demo',    'role': 'CONVIVENCIA', 'establishment': 'ANGOL',    'email': 'convivencia@demo.cl'},
    {'username': 'red.demo',          'first_name': 'Red',          'last_name': 'Demo',    'role': 'RED',          'establishment': 'RED',      'email': 'red@demo.cl'},
]

for ud in DEMO_USERS:
    user, created = User.objects.get_or_create(
        username=ud['username'],
        defaults={
            'password': 'Demo1234!',
            'first_name': ud['first_name'],
            'last_name': ud['last_name'],
            'role': ud['role'],
            'establishment': ud['establishment'],
            'email': ud['email']
        }
    )
    if not created:
        # Asegurar que el establecimiento esté actualizado para pruebas
        user.establishment = ud['establishment']
        user.save()
        print(f"ℹ️  Usuario actualizado: {ud['username']} en {ud['establishment']}")
    else:
        print(f"✅ Usuario demo creado: {ud['username']} (pass: Demo1234!)")

# ── Salas de Reunión (Daily.co) ──────────────────────────────────
ROOMS = [
    # Salas Daily.co por Establecimiento
    {'name': 'Sala Angol', 'slug': 'daily-angol', 'room_type': 'daily', 'daily_identifier': 'angol', 'target_establishment': 'ANGOL'},
    {'name': 'Sala Arauco', 'slug': 'daily-arauco', 'room_type': 'daily', 'daily_identifier': 'arauco', 'target_establishment': 'ARAUCO'},
    {'name': 'Sala Imperial', 'slug': 'daily-imperial', 'room_type': 'daily', 'daily_identifier': 'imperial', 'target_establishment': 'IMPERIAL'},
    {'name': 'Sala Lautaro', 'slug': 'daily-lautaro', 'room_type': 'daily', 'daily_identifier': 'lautaro', 'target_establishment': 'LAUTARO'},
    {'name': 'Sala Ercilla', 'slug': 'daily-ercilla', 'room_type': 'daily', 'daily_identifier': 'ercilla', 'target_establishment': 'ERCILLA'},
    {'name': 'Sala Santiago', 'slug': 'daily-santiago', 'room_type': 'daily', 'daily_identifier': 'santiago', 'target_establishment': 'SANTIAGO'},
    {'name': 'Sala Renaico', 'slug': 'daily-renaico', 'room_type': 'daily', 'daily_identifier': 'renaico', 'target_establishment': 'RENAICO'},
    {'name': 'Sala Temuco', 'slug': 'daily-temuco', 'room_type': 'daily', 'daily_identifier': 'temuco', 'target_establishment': 'TEMUCO'},
    
    # Salas Daily.co por Perfil
    {'name': 'Videollamada UTP', 'slug': 'daily-utp', 'room_type': 'daily', 'daily_identifier': 'utp', 'target_role': 'UTP'},
    {'name': 'Videollamada Director', 'slug': 'daily-director', 'room_type': 'daily', 'daily_identifier': 'director', 'target_role': 'DIRECTOR'},
    {'name': 'Videollamada Inspector', 'slug': 'daily-inspector', 'room_type': 'daily', 'daily_identifier': 'inspector', 'target_role': 'INSPECTOR'},
    {'name': 'Videollamada Convivencia', 'slug': 'daily-convivencia', 'room_type': 'daily', 'daily_identifier': 'convivenciaescolar', 'target_role': 'CONVIVENCIA'},
    {'name': 'Videollamada Equipo Red', 'slug': 'daily-red', 'room_type': 'daily', 'daily_identifier': 'red', 'target_role': 'RED'},
]

for r_data in ROOMS:
    room, created = MeetingRoom.objects.get_or_create(
        slug=r_data['slug'],
        defaults={k: v for k, v in r_data.items() if k != 'slug'}
    )
    if created:
        print(f"✅ Sala creada: {room.name} (Daily.co (Nuevo))")
    else:
        # Actualizar campos por si acaso
        for key, value in r_data.items():
            setattr(room, key, value)
        room.save()
        print(f"ℹ️  Sala actualizada: {room.name}")

# ── Reservas Activas para Pruebas (AHORA) ──────────────────────────────────
print("\n📅 Creando reuniones de prueba activas...")
now = timezone.now()
test_rooms = ['daily-angol', 'daily-utp']
admin_user = User.objects.get(username='admin')

for slug in test_rooms:
    room = MeetingRoom.objects.get(slug=slug)
    # Crear una reserva que empezó hace 5 minutos y dura 2 horas
    booking, created = MeetingBooking.objects.get_or_create(
        room=room,
        booked_by=admin_user,
        status='activa',
        defaults={
            'scheduled_at': now - timedelta(minutes=5),
            'duration_minutes': 120,
            'agenda': 'Reunión de prueba para validación de multiperfil y accesos.'
        }
    )
    if not created:
        booking.scheduled_at = now - timedelta(minutes=5)
        booking.status = 'activa'
        booking.save()
        print(f"✅ Reserva existente actualizada para: {room.name} (ACTIVA)")
    else:
        print(f"✅ Nueva reserva de prueba creada para: {room.name} (ACTIVA)")

# ── Asistentes IA ──────────────────────────────────────────────────────────
ASSISTANTS = [
    {
        'name': 'Asistente Jurídico (Mineduc)',
        'slug': 'juridico-mineduc',
        'profile_role': 'RED',
        'notebook_url': 'https://notebooklm.google.com/example1',
        'image_name': 'juridico.png',
        'description': 'Especialista en normativa educacional chilena y procesos de la Superintendencia.',
        'use_cases': 'Manual de Convivencia\nEstatuto docente\nNormativas Supereduc',
    },
    {
        'name': 'Curriculum Master (UTP)',
        'slug': 'curriculum-utp',
        'profile_role': 'UTP',
        'notebook_url': 'https://notebooklm.google.com/example2',
        'image_name': 'curriculum.png',
        'description': 'Apoyo en planificación curricular, DUA y evaluación de aprendizajes.',
        'use_cases': 'Planificación de clases\nAdaptación OA\nDUA',
    },
    {
        'name': 'Mediador de Convivencia',
        'slug': 'mediador-convivencia',
        'profile_role': 'CONVIVENCIA',
        'notebook_url': 'https://notebooklm.google.com/example3',
        'image_name': 'convivencia.png',
        'description': 'Apoyo en protocolos de convivencia, mediación escolar y clima institucional.',
        'use_cases': 'Protocolos maltrato\nMediación escolar\nClima institucional',
    },
]

for data in ASSISTANTS:
    assistant, created = AIAssistant.objects.get_or_create(
        slug=data['slug'],
        defaults={k: v for k, v in data.items() if k != 'slug'},
    )
    if created:
        print(f"✅ Asistente IA creado: {assistant.name}")

print("\n🚀 Datos iniciales cargados con éxito.")
