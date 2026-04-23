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

print("🌱 Iniciando SEED (Exclusivo Temuco)...")

# ── 1. Usuarios Demo ──────────────────────────────────────────────────────────
DEMO_USERS = [
    {'username': 'director.demo',     'role': 'DIRECTOR',     'establishment': 'TEMUCO'},
    {'username': 'utp.demo',          'role': 'UTP',          'establishment': 'TEMUCO'},
    {'username': 'inspector.demo',    'role': 'INSPECTOR',    'establishment': 'TEMUCO'},
    {'username': 'convivencia.demo', 'role': 'CONVIVENCIA', 'establishment': 'TEMUCO'},
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

# ── 2. Asistentes IA Oficiales (Temuco) ───────────────────────────────────────
print("\n🤖 Sincronizando Asistentes IA Temuco...")
ASSISTANTS = [
    {
        'name': 'Asistente Estratégico (Director) - Temuco', 
        'slug': 'director-temuco', 
        'profile_role': 'DIRECTOR', 
        'establishment': 'TEMUCO',
        'is_chat_enabled': True,
        'description': 'Gestión institucional y liderazgo - Temuco.',
        'system_instruction': (
            "Área de Acción: Universal (aplica a cualquier situación).\n"
            "Funciones: Gestionar lo Urgente/Importante, delegar liderazgo, monitorear procesos.\n"
            "Foco: Eisenhower (Urgente/Importante) y aseguramiento de calidad."
        )
    },
    {
        'name': 'Asistente IA UTP Temuco', 
        'slug': 'utp-temuco', 
        'profile_role': 'UTP', 
        'establishment': 'TEMUCO',
        'is_chat_enabled': True,
        'description': 'Gestión curricular y pedagógica - Temuco.',
        'system_instruction': (
            "Área de Acción: Técnico-Pedagógica (Curricular y Pedagógica).\n"
            "Documentos: Reglamento de Evaluación, Decretos 67, 83, 170 y PIE.\n"
            "Foco: Articulación normativa, propuestas evaluativas y vinculación con la familia."
        )
    },
    {
        'name': 'Asistente de Disciplina e Inspectoría - Temuco', 
        'slug': 'inspector-temuco', 
        'profile_role': 'INSPECTOR', 
        'establishment': 'TEMUCO',
        'is_chat_enabled': True,
        'description': 'Gestión de personal y normativa interna - Temuco.',
        'system_instruction': (
            "Área de Acción: Gestión y Clima Escolar / Personal del establecimiento.\n"
            "Documento Base: RIOHS (Reglamento Interno de Orden, Higiene y Seguridad).\n"
            "Foco: Manejo de conflictos, mediación laboral y clima organizacional."
        )
    },
    {
        'name': 'Asistente de Convivencia Escolar - Temuco', 
        'slug': 'convivencia-temuco', 
        'profile_role': 'CONVIVENCIA', 
        'establishment': 'TEMUCO',
        'is_chat_enabled': True,
        'description': 'Clima escolar y resolución de conflictos - Temuco.',
        'system_instruction': (
            "Área de Acción: Gestión y Clima Escolar / Estudiantes y Apoderados.\n"
            "Documento Base: RICE (Reglamento Interno de Convivencia Escolar).\n"
            "Foco: Prevención, formación y reparación ante conflictos escolares."
        )
    },
    {
        'name': 'Asistente Representante Legal (Temuco)', 
        'slug': 'representante-temuco', 
        'profile_role': 'REPRESENTANTE', 
        'establishment': 'TEMUCO',
        'is_chat_enabled': True,
        'description': 'Gestión de recursos y contratos - Temuco.',
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
    
    # Sincronizar a la base de conocimiento si es necesario
    try:
        assistant.save(using='knowledge_base')
    except:
        pass

print("\n🚀 SEED Temuco completado con éxito.")
