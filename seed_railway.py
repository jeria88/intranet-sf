import os
import django
import random
from django.utils import timezone
from datetime import timedelta

# Configurar entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from meetings.models import MeetingRoom, MeetingBooking
from ai_modules.models import AIAssistant

User = get_user_model()

print("🌱 Iniciando MEGA-SEED (40 Usuarios + Demos)...")

# ── Listas para generación aleatoria ─────────────────────────────────────────
FIRST_NAMES = ['Ariel', 'Camila', 'Beatriz', 'Diego', 'Elena', 'Francisco', 'Gloria', 'Hugo', 'Isabel', 'Juan', 'Karla', 'Luis', 'María', 'Nicolás', 'Olga', 'Pablo', 'Rosa', 'Sergio', 'Teresa', 'Víctor']
LAST_NAMES = ['Rosenmann', 'Jeria', 'Pérez', 'González', 'Muñoz', 'Rojas', 'Díaz', 'Soto', 'Silva', 'Sepúlveda', 'Morales', 'Fuentes', 'Valenzuela', 'Araya', 'Castillo', 'Tapia', 'Reyes', 'Gutiérrez', 'Castro', 'Pizarro']

ESTABLISHMENTS = ['TEMUCO', 'LAUTARO', 'RENAICO', 'SANTIAGO', 'IMPERIAL', 'ERCILLA', 'ARAUCO', 'ANGOL']
ROLES = ['REPRESENTANTE', 'UTP', 'DIRECTOR', 'INSPECTOR', 'CONVIVENCIA']

# ── Superusuario ─────────────────────────────────────────────────────────────
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@sfared.cl', 'Admin1234!')
    print("✅ Superusuario 'admin' creado (pass: Admin1234!)")

# ── 1. Carga de Usuarios Demo (.env) ──────────────────────────────────────────
# Mantenemos los de demo para no romper accesos conocidos
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

# ── 2. Carga Masiva (40 Usuarios: 8 locales x 5 roles) ────────────────────────
print(f"👥 Generando 40 usuarios dinámicos...")
for est in ESTABLISHMENTS:
    for role in ROLES:
        username = f"{role.lower()}.{est.lower()}"
        
        # Evitar duplicados si ya existe por casualidad
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': random.choice(FIRST_NAMES),
                'last_name': random.choice(LAST_NAMES),
                'role': role,
                'establishment': est,
                'email': f"{username}@sfared.cl"
            }
        )
        user.set_password('Admin1234!')
        user.save()
        
        if created:
            print(f"  + Creado: {username}")

# ── 3. Salas de Reunión (Daily.co) ──────────────────────────────────
ROOMS = [
    {'name': 'Sala Angol', 'slug': 'daily-angol', 'room_type': 'daily', 'daily_identifier': 'angol', 'target_establishment': 'ANGOL'},
    {'name': 'Sala Arauco', 'slug': 'daily-arauco', 'room_type': 'daily', 'daily_identifier': 'arauco', 'target_establishment': 'ARAUCO'},
    {'name': 'Sala Imperial', 'slug': 'daily-imperial', 'room_type': 'daily', 'daily_identifier': 'imperial', 'target_establishment': 'IMPERIAL'},
    {'name': 'Sala Lautaro', 'slug': 'daily-lautaro', 'room_type': 'daily', 'daily_identifier': 'lautaro', 'target_establishment': 'LAUTARO'},
    {'name': 'Sala Ercilla', 'slug': 'daily-ercilla', 'room_type': 'daily', 'daily_identifier': 'ercilla', 'target_establishment': 'ERCILLA'},
    {'name': 'Sala Santiago', 'slug': 'daily-santiago', 'room_type': 'daily', 'daily_identifier': 'santiago', 'target_establishment': 'SANTIAGO'},
    {'name': 'Sala Renaico', 'slug': 'daily-renaico', 'room_type': 'daily', 'daily_identifier': 'renaico', 'target_establishment': 'RENAICO'},
    {'name': 'Sala Temuco', 'slug': 'daily-temuco', 'room_type': 'daily', 'daily_identifier': 'temuco', 'target_establishment': 'TEMUCO'},
    {'name': 'Videollamada UTP', 'slug': 'daily-utp', 'room_type': 'daily', 'daily_identifier': 'utp', 'target_role': 'UTP'},
    {'name': 'Videollamada Director', 'slug': 'daily-director', 'room_type': 'daily', 'daily_identifier': 'director', 'target_role': 'DIRECTOR'},
    {'name': 'Videollamada Inspector', 'slug': 'daily-inspector', 'room_type': 'daily', 'daily_identifier': 'inspector', 'target_role': 'inspector'},
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

# ── 4. Limpieza y Creación de Reservas Activas para Pruebas ──────────────────
print("\n📅 Generando agenda de pruebas...")
MeetingBooking.objects.filter(status__in=['programada', 'activa']).delete() # Limpieza para que no se superpongan en Saturday tests
now = timezone.now()

# Crear una reunión activa para UTP Angol para probar "EN CURSO"
utp_angol = User.objects.get(username='utp.angol')
room_utp = MeetingRoom.objects.get(slug='daily-utp')
MeetingBooking.objects.create(
    room=room_utp,
    booked_by=utp_angol,
    scheduled_at=now - timedelta(minutes=10),
    duration_minutes=60,
    status='activa',
    agenda='Prueba de reunión activa para UTP Angol'
)

# ── 5. Asistentes IA Oficiales y RAG automático ───────────────────────────────
print("\n🤖 Sincronizando Asistentes IA y Base de Conocimientos...")
ASSISTANTS = [
    {'name': 'Asistente Estratégico (Director)', 'slug': 'director', 'profile_role': 'DIRECTOR', 'notebook_url': 'https://notebooklm.google.com/example/director', 'image_name': 'asistente-director.jpg', 'description': 'Apoyo en gestión institucional.', 'use_cases': 'PME\nGestión'},
    {'name': 'Asistente Curricular (UTP)', 'slug': 'utp', 'profile_role': 'UTP', 'notebook_url': 'https://notebooklm.google.com/example/utp', 'image_name': 'asistente-utp.jpg', 'description': 'Apoyo en planificación.', 'use_cases': 'DUA\nPlanificación'},
    {'name': 'Asistente de Disciplina e Inspectoría', 'slug': 'inspector', 'profile_role': 'INSPECTOR', 'notebook_url': 'https://notebooklm.google.com/example/inspector', 'image_name': 'asistente-inspector.jpg', 'description': 'Apoyo en reglamento.', 'use_cases': 'RICE\nAsistencia'},
    {'name': 'Asistente de Convivencia Escolar', 'slug': 'convivencia', 'profile_role': 'CONVIVENCIA', 'notebook_url': 'https://notebooklm.google.com/example/convivencia', 'image_name': 'asistente-convivencia.jpg', 'description': 'Apoyo en mediación.', 'use_cases': 'Mediación\nClima'},
    {
        'name': 'Asistente IA UTP Temuco', 
        'slug': 'utp-temuco', 
        'profile_role': 'UTP', 
        'establishment': 'TEMUCO',
        'is_chat_enabled': True,
        'image_name': 'asistente-utp.jpg', 
        'description': 'Asistente RAG con base de conocimientos oficial de Temuco.',
        'use_cases': 'Reglamentos\nPEI\nRIOHS\nGestión Curricular',
        'system_instruction': (
            "Eres el Asistente Virtual Oficial de la Unidad Técnico Pedagógica (UTP) del Colegio de Temuco de la Red SFA. "
            "Tu identidad es 'Asistente IA Temuco'. No eres un modelo de lenguaje genérico, sino una herramienta especializada "
            "en el Proyecto Educativo Institucional (PEI) y los reglamentos del colegio. "
            "Responde siempre basándote EN EL CONTEXTO DE DOCUMENTOS proporcionado. Si el contexto no tiene la respuesta, "
            "indícalo y ofrece ayuda para contactar a la dirección. Prohibido identificarte como DeepSeek o mencionar que eres una IA genérica."
        )
    },
]

for data in ASSISTANTS:
    assistant, created = AIAssistant.objects.get_or_create(
        slug=data['slug'],
        defaults={k: v for k, v in data.items() if k != 'slug'},
    )
    if not created:
        # Actualizar campos por si cambiaron (ej: habilitar chat)
        for key, value in data.items():
            setattr(assistant, key, value)
        assistant.save()

# Procesamiento automático de PDFs para RAG (si el contexto está vacío)
temuco_assistant = AIAssistant.objects.filter(slug='utp-temuco').first()
if temuco_assistant and not temuco_assistant.context_text:
    print("📚 Base de conocimientos vacía para Temuco. Iniciando procesamiento RAG...")
    from ai_modules.utils import process_knowledge_base_file
    
    kb_path = os.path.join(os.path.dirname(__file__), 'ai_modules', 'knowledge_base')
    if os.path.exists(kb_path):
        pdfs = [f for f in os.listdir(kb_path) if f.endswith('.pdf')]
        print(f"  -> Encontrados {len(pdfs)} documentos en {kb_path}")
        
        for pdf_name in pdfs:
            pdf_path = os.path.join(kb_path, pdf_name)
            try:
                with open(pdf_path, 'rb') as f:
                    # Envolviendo el archivo en un objeto compatible si es necesario
                    # Pero process_knowledge_base_file espera un objeto similar a un archivo de Django (con .name)
                    # Vamos a simularlo mínimamente
                    setattr(f, 'name', pdf_name)
                    process_knowledge_base_file(temuco_assistant, f)
                print(f"  ✅ Procesado: {pdf_name}")
            except Exception as e:
                print(f"  ❌ Error procesando {pdf_name}: {e}")
        
        print(f"✨ RAG inicializado. Contexto total: {len(temuco_assistant.context_text)} caracteres.")
    else:
        print(f"⚠️  Carpeta de conocimientos no encontrada en: {kb_path}")

print("\n🚀 MEGA-SEED completado con éxito.")
print("💡 Tip: Para probar, usa p.ej. 'utp.temuco' / 'Admin1234!'")
