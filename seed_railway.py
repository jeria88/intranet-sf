"""
Script de datos iniciales para intranet_v3.
Ejecutar: cd intranet_v3 && venv/bin/python3 seed_v3.py

Crea: superusuario admin, salas de reuniones Jitsi, asistentes IA.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from users.models import User
from meetings.models import MeetingRoom
from ai_modules.models import AIAssistant

# ── Superusuario ────────────────────────────────────────────────────────
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@intranet.cl',
        password='Admin1234!',
        first_name='Administrador',
        last_name='Sistema',
        role='REPRESENTANTE',
        establishment='RED',
    )
    print("✅ Superusuario 'admin' creado (pass: Admin1234!)")
else:
    print("ℹ️  Superusuario 'admin' ya existe")

# ── Salas de Reunión Jitsi ──────────────────────────────────────────────
ROOMS = [
    {'name': 'Directores', 'slug': 'sfatcodirectores', 'allowed_roles': ['DIRECTOR']},
    {'name': 'Inspectores Generales', 'slug': 'sfatcoinspectores', 'allowed_roles': ['INSPECTOR']},
    {'name': 'Convivencia Escolar', 'slug': 'sfatcoconvivenciaescolar', 'allowed_roles': ['CONVIVENCIA']},
    {'name': 'UTP', 'slug': 'sfatcoutp', 'allowed_roles': ['UTP']},
    {'name': 'Equipo Red', 'slug': 'sfatcoequipored', 'allowed_roles': [], 'is_unlimited': True},
]

for r in ROOMS:
    room, created = MeetingRoom.objects.get_or_create(
        slug=r['slug'],
        defaults={
            'name': r['name'],
            'allowed_roles': r.get('allowed_roles', []),
            'is_unlimited': r.get('is_unlimited', False),
        }
    )
    if created:
        print(f"✅ Sala creada: {room.name}")

# ── Asistentes IA ───────────────────────────────────────────────────────
ASSISTANTS = [
    {
        'slug': 'director',
        'name': 'Asistente IA del Director',
        'profile_role': 'DIRECTOR',
        'notebook_url': 'https://notebooklm.google.com/notebook/57b5d3dd-fe89-495b-b425-101cb235fe4a',
        'image_name': 'asistente-director.jpg',
        'description': 'Soporte en PEI, fiscalización, RO y riesgos jurídicos.',
        'use_cases': (
            'Consultar normativa sobre evaluación docente y desempeño directivo.\n'
            'Revisar marcos legales aplicables a la gestión escolar.\n'
            'Preparar fundamentos para planes de mejoramiento educativo (PME).\n'
            'Resolver dudas sobre protocolos de convivencia escolar.'
        ),
    },
    {
        'slug': 'utp',
        'name': 'Asistente IA del UTP',
        'profile_role': 'UTP',
        'notebook_url': 'https://notebooklm.google.com/notebook/ddbbd461-ecad-49a6-b48b-8468bc955aef',
        'image_name': 'asistente-utp.jpg',
        'description': 'Validación de Reglamento de Evaluación (D67-D83).',
        'use_cases': (
            'Revisar y alinear planificaciones con Bases Curriculares.\n'
            'Preparar talleres de acompañamiento docente.\n'
            'Interpretar resultados SIMCE y PAES.\n'
            'Consultar criterios del Marco para la Buena Enseñanza.'
        ),
    },
    {
        'slug': 'inspector',
        'name': 'Asistente IA del Inspector General',
        'profile_role': 'INSPECTOR',
        'notebook_url': 'https://notebooklm.google.com/notebook/74849770-196a-4249-b01b-0b0e56248a8d',
        'image_name': 'asistente-inspector.jpg',
        'description': 'RICE, RIOHS y normativa laboral/contractual.',
        'use_cases': (
            'Consultar protocolos ante situaciones de bullying o agresión.\n'
            'Verificar normativa sobre registro de asistencia.\n'
            'Redactar comunicaciones oficiales a apoderados.\n'
            'Gestionar dudas sobre medidas disciplinarias y debido proceso.'
        ),
    },
    {
        'slug': 'convivencia',
        'name': 'Asistente IA de Convivencia Escolar',
        'profile_role': 'CONVIVENCIA',
        'notebook_url': 'https://notebooklm.google.com/notebook/11dad977-017b-4bc3-829e-bfb212488f62',
        'image_name': 'asistente-convivencia.jpg',
        'description': 'Gestión de RICE y resguardo del debido proceso.',
        'use_cases': (
            'Elaborar o revisar el Plan de Gestión de Convivencia Escolar.\n'
            'Consultar protocolos ante situaciones de abuso o maltrato.\n'
            'Diseñar actividades de formación ciudadana.\n'
            'Interpretar la Política Nacional de Convivencia Escolar.'
        ),
    },
]

for data in ASSISTANTS:
    assistant, created = AIAssistant.objects.get_or_create(
        slug=data['slug'],
        defaults={k: v for k, v in data.items() if k != 'slug'},
    )
    if created:
        print(f"✅ Asistente IA creado: {assistant.name}")

print("\n🚀 Datos iniciales cargados. Ejecuta: venv/bin/python3 manage.py runserver")
