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

print("🌱 Iniciando carga de datos iniciales optimizados...")

# ── Superusuario ─────────────────────────────────────────────────────────────
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@sfared.cl', 'admin123')
    print("✅ Superusuario 'admin' creado (pass: admin123)")
else:
    print("ℹ️  Superusuario 'admin' ya existe")

# ── Usuarios de demo (Cubre todos los roles para pruebas) ──────────────────
DEMO_USERS = [
    {'username': 'director.demo',     'first_name': 'Director',     'last_name': 'Demo',    'role': 'DIRECTOR',     'establishment': 'ANGOL',    'email': 'director@demo.cl'},
    {'username': 'utp.demo',          'first_name': 'UTP',          'last_name': 'Demo',    'role': 'UTP',          'establishment': 'ANGOL',    'email': 'utp@demo.cl'},
    {'username': 'inspector.demo',    'first_name': 'Inspector',    'last_name': 'Demo',    'role': 'INSPECTOR',    'establishment': 'ANGOL',    'email': 'inspector@demo.cl'},
    {'username': 'convivencia.demo', 'first_name': 'Convivencia', 'last_name': 'Demo',    'role': 'CONVIVENCIA', 'establishment': 'ANGOL',    'email': 'convivencia@demo.cl'},
    {'username': 'red.demo',          'first_name': 'Red',          'last_name': 'Demo',    'role': 'RED',          'establishment': 'RED',      'email': 'red@demo.cl'},
    
    # Usuarios en otros establecimientos para probar el filtrado multi-colegio
    {'username': 'director.temuco',   'first_name': 'Director',     'last_name': 'Temuco',  'role': 'DIRECTOR',     'establishment': 'TEMUCO',   'email': 'director.tmu@demo.cl'},
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
        user.establishment = ud['establishment']
        user.role = ud['role']
        user.save()
        print(f"ℹ️  Usuario actualizado: {ud['username']} como {ud['role']} en {ud['establishment']}")
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
    if not created:
        for key, value in r_data.items():
            setattr(room, key, value)
        room.save()

# ── Reservas de Prueba Coherentes ──────────────────────────────────
print("\n📅 Generando historial y agenda de reuniones...")
now = timezone.now()
admin_user = User.objects.get(username='admin')
utp_user = User.objects.get(username='utp.demo')

# 1. Reunión PASADA (Hoy temprano) - Para probar historial
room_angol = MeetingRoom.objects.get(slug='daily-angol')
MeetingBooking.objects.get_or_create(
    room=room_angol,
    booked_by=admin_user,
    scheduled_at=now - timedelta(hours=5),
    defaults={
        'duration_minutes': 60,
        'status': 'cerrada',
        'agenda': 'Reunión de coordinación técnica matutina.'
    }
)

# 2. Reunión PRÓXIMA (En 2 horas) - Para probar estado "PRÓXIMA"
MeetingBooking.objects.get_or_create(
    room=room_angol,
    booked_by=utp_user,
    scheduled_at=now + timedelta(hours=2),
    defaults={
        'duration_minutes': 45,
        'status': 'programada',
        'agenda': 'Revisión de avances PME segundo trimestre.'
    }
)

# 3. Reunión EN CURSO (Solo en Salas de Perfil para pruebas rápidas)
room_utp = MeetingRoom.objects.get(slug='daily-utp')
active_booking, created = MeetingBooking.objects.get_or_create(
    room=room_utp,
    booked_by=admin_user,
    scheduled_at=now - timedelta(minutes=10),
    defaults={
        'duration_minutes': 90,
        'status': 'activa',
        'agenda': 'Taller de Inteligencia Artificial para el Equipo Red.'
    }
)
if not created:
    active_booking.status = 'activa'
    active_booking.scheduled_at = now - timedelta(minutes=10)
    active_booking.save()

# ── Asistentes IA Oficiales ────────────────────────────────────────────────
ASSISTANTS = [
    {
        'name': 'Asistente Estratégico (Director)',
        'slug': 'director',
        'profile_role': 'DIRECTOR',
        'notebook_url': 'https://notebooklm.google.com/example/director',
        'image_name': 'asistente-director.jpg',
        'description': 'Apoyo en gestión institucional, liderazgo y normativa.',
        'use_cases': 'Gestión de recursos\nLiderazgo educativo\nPlan de Mejoramiento Educativo (PME)',
    },
    {
        'name': 'Asistente Curricular (UTP)',
        'slug': 'utp',
        'profile_role': 'UTP',
        'notebook_url': 'https://notebooklm.google.com/example/utp',
        'image_name': 'asistente-utp.jpg',
        'description': 'Apoyo en planificación, evaluación y DUA.',
        'use_cases': 'Acompañamiento docente\nPlanificación curricular\nAnálisis de resultados',
    },
    {
        'name': 'Asistente de Disciplina e Inspectoría',
        'slug': 'inspector',
        'profile_role': 'INSPECTOR',
        'notebook_url': 'https://notebooklm.google.com/example/inspector',
        'image_name': 'asistente-inspector.jpg',
        'description': 'Apoyo en reglamento interno, asistencia y procesos administrativos.',
        'use_cases': 'Reglamento Interno (RICE)\nGestión de asistencia\nProtocolos de seguridad',
    },
    {
        'name': 'Asistente de Convivencia Escolar',
        'slug': 'convivencia',
        'profile_role': 'CONVIVENCIA',
        'notebook_url': 'https://notebooklm.google.com/example/convivencia',
        'image_name': 'asistente-convivencia.jpg',
        'description': 'Apoyo en mediación escolar, protocolos de maltrato escolar y clima institucional.',
        'use_cases': 'Protocolos de actuación\nMediación escolar\nEntrevistas apoderados',
    },
]

for data in ASSISTANTS:
    assistant, created = AIAssistant.objects.get_or_create(
        slug=data['slug'],
        defaults={k: v for k, v in data.items() if k != 'slug'},
    )

print("\n🚀 Datos iniciales cargados con éxito.")
