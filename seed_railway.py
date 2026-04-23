import os
import django
import random
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import json

# Configurar entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from meetings.models import MeetingRoom, MeetingBooking
from ai_modules.models import AIAssistant
from library.models import Category

User = get_user_model()

print("🌱 Iniciando MEGA-SEED (Protocolo San Francisco de Asís)...")

# ── Listas para generación aleatoria ─────────────────────────────────────────
FIRST_NAMES = ['Ariel', 'Camila', 'Beatriz', 'Diego', 'Elena', 'Francisco', 'Gloria', 'Hugo', 'Isabel', 'Juan', 'Karla', 'Luis', 'María', 'Nicolás', 'Olga', 'Pablo', 'Rosa', 'Sergio', 'Teresa', 'Víctor']
LAST_NAMES = ['Rosenmann', 'Jeria', 'Pérez', 'González', 'Muñoz', 'Rojas', 'Díaz', 'Soto', 'Silva', 'Sepúlveda', 'Morales', 'Fuentes', 'Valenzuela', 'Araya', 'Castillo', 'Tapia', 'Reyes', 'Gutiérrez', 'Castro', 'Pizarro']

ESTABLISHMENTS = ['TEMUCO', 'LAUTARO', 'RENAICO', 'SANTIAGO', 'IMPERIAL', 'ERCILLA', 'ARAUCO', 'ANGOL']
ROLES = ['REPRESENTANTE', 'UTP', 'DIRECTOR', 'INSPECTOR', 'CONVIVENCIA']

# ── Superusuario ─────────────────────────────────────────────────────────────
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@sfared.cl', 'Admin1234!')
    print("✅ Superusuario 'admin' creado (pass: Admin1234!)")

# ── 1. Usuarios Demo ──────────────────────────────────────────────────────────
DEMO_USERS = [
    {'username': 'director.demo',     'role': 'DIRECTOR',     'establishment': 'ANGOL'},
    {'username': 'utp.demo',          'role': 'UTP',          'establishment': 'ANGOL'},
    {'username': 'inspector.demo',    'role': 'INSPECTOR',    'establishment': 'ANGOL'},
    {'username': 'convivencia.demo', 'role': 'CONVIVENCIA', 'establishment': 'ANGOL'},
    {'username': 'red.demo',          'role': 'RED',          'establishment': 'RED'},
]

for ud in DEMO_USERS:
    User.objects.get_or_create(
        username=ud['username'],
        defaults={
            'password': 'Admin1234!',
            'first_name': ud['username'].split('.')[0].capitalize(),
            'last_name': 'Demo',
            'role': ud['role'],
            'establishment': ud['establishment'],
            'email': f"{ud['username']}@demo.cl"
        }
    )

# ── 2. Salas de Reunión ──────────────────────────────────────────────────────
ROOMS = [
    {'name': 'Sala Temuco', 'slug': 'daily-temuco', 'room_type': 'daily', 'daily_identifier': 'temuco', 'target_establishment': 'TEMUCO'},
    {'name': 'Videollamada UTP', 'slug': 'daily-utp', 'room_type': 'daily', 'daily_identifier': 'utp', 'target_role': 'UTP'},
]

for r_data in ROOMS:
    MeetingRoom.objects.get_or_create(
        slug=r_data['slug'],
        defaults={k: v for k, v in r_data.items() if k != 'slug'}
    )

# ── 3. Asistentes IA Oficiales (Protocolo Institucional) ───────────────────────
print("\n🤖 Sincronizando Asistentes IA...")
ASSISTANTS = [
    {
        'name': 'Asistente Estratégico (Director)', 
        'slug': 'director', 
        'profile_role': 'DIRECTOR', 
        'is_chat_enabled': True,
        'description': 'Gestión institucional y liderazgo.',
        'system_instruction': (
            "Área de Acción: Universal (aplica a cualquier situación).\n"
            "Funciones: Gestionar lo Urgente/Importante, delegar liderazgo, monitorear procesos.\n"
            "Foco: Eisenhower (Urgente/Importante) y aseguramiento de calidad."
        )
    },
    {
        'name': 'Asistente Curricular (UTP)', 
        'slug': 'utp', 
        'profile_role': 'UTP', 
        'is_chat_enabled': True,
        'description': 'Gestión curricular y pedagógica.',
        'system_instruction': (
            "Área de Acción: Técnico-Pedagógica (Curricular y Pedagógica).\n"
            "Documentos: Reglamento de Evaluación, Decretos 67, 83, 170 y PIE.\n"
            "Foco: Articulación normativa, propuestas evaluativas y vinculación con la familia."
        )
    },
    {
        'name': 'Asistente de Disciplina e Inspectoría', 
        'slug': 'inspector', 
        'profile_role': 'INSPECTOR', 
        'is_chat_enabled': True,
        'description': 'Gestión de personal y normativa interna.',
        'system_instruction': (
            "Área de Acción: Gestión y Clima Escolar / Personal del establecimiento.\n"
            "Documento Base: RIOHS (Reglamento Interno de Orden, Higiene y Seguridad).\n"
            "Foco: Manejo de conflictos, mediación laboral y clima organizacional."
        )
    },
    {
        'name': 'Asistente de Convivencia Escolar', 
        'slug': 'convivencia', 
        'profile_role': 'CONVIVENCIA', 
        'is_chat_enabled': True,
        'description': 'Clima escolar y resolución de conflictos.',
        'system_instruction': (
            "Área de Acción: Gestión y Clima Escolar / Estudiantes y Apoderados.\n"
            "Documento Base: RICE (Reglamento Interno de Convivencia Escolar).\n"
            "Foco: Prevención, formación y reparación ante conflictos escolares."
        )
    },
    {
        'name': 'Asistente Representante Legal', 
        'slug': 'representante', 
        'profile_role': 'REPRESENTANTE', 
        'is_chat_enabled': True,
        'description': 'Gestión de recursos y contratos.',
        'system_instruction': (
            "Área de Acción: Gestión de Contratos y Recursos.\n"
            "Foco: Normativa internacional, Ley 21809, recursos SEP/PIE.\n"
            "Objetivo: Bienestar superior de estudiantes y funcionarios, optimización de recursos."
        )
    },
]

for data in ASSISTANTS:
    assistant, created = AIAssistant.objects.get_or_create(
        slug=data['slug'],
        defaults={k: v for k, v in data.items() if k != 'slug'},
    )
    if not created:
        for key, value in data.items():
            setattr(assistant, key, value)
        assistant.save()

print("\n🚀 SEED completado con éxito.")
