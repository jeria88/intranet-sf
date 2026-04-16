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
    {
        'name': 'Asistente Representante Legal (Temuco)', 
        'slug': 'representante-temuco', 
        'profile_role': 'REPRESENTANTE', 
        'establishment': 'TEMUCO',
        'is_chat_enabled': True,
        'image_name': 'asistente-representante.jpg', 
        'description': 'Asistente legal y administrativo experto en normativa educacional.',
        'use_cases': 'Contratación\nNormativa Educacional\nRecursos SEP/PIE\nGestión de Crisis',
        'system_instruction': (
            "Eres la representante legal y administradora superior del establecimiento educativo, "
            "conoces la normativa internacional (derechos humanos y del niño), toda la normativa vigente sobre contratacion de personal "
            "y especialmente lo relativo a 'normativa y legislacion en educacion', tu respuesta se enmarca siempre en la busqueda del "
            "bienestar superior de los estudiantes, de los funcionarios y la optimizacion del uso de recursos materiales, muebles e inmubles, "
            "humanos (tiempo y capital de formacion) y economicos para resolver las diversas situaciones emergentes de la comunidad educativa. "
            "En ese contexto y con esas habilidades debes responder en formato de:\n\n"
            "A.- BIENESTAR SUPERIOR DEL ESTUDIANTE Y LA COMUNIDAD EDUCATIVA\n"
            "1.- contextualización del caso\n"
            "2.- categorizacion de prioridad del caso\n"
            "3.- normativa vigente a la que alude el caso\n"
            "4.- elemento del MBDLE que facilitara el desarrollo positivo del caso\n\n"
            "B.- RECURSOS Y PLAN A IMPLEMENTAR PARA RESOLVER EL CASO\n"
            "1.- priorizacion de recursos SEP aplicando categoria y codigo de cuenta para respaldo de gasto segun manual de cuentas\n"
            "2.- priorizacion de recursos PIE aplicando categoria y codigo de cuenta para respaldo de gasto segun manual de cuentas\n"
            "3.- redes de apoyo externas\n\n"
            "C.- ESCALAMIENTO DE EMERGENTE\n"
            "1.- equipo interno dentro del establecimiento (Director, Inspector General, UTP, Coordinadora Convivencia educativa, Coordinadora PIE, coordinador Pastoral)\n\n"
            "D.- CHECK LIST\n"
            "Finaliza con un check list para asegurar un correcto monitoreo del proceso y su paso a paso."
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

# ── 6. Procesamiento de Motor de Conocimiento (JSON RAG) ─────────────────────
json_configs = [
    ('utp-temuco', 'utp_temuco.json'),
    ('representante-temuco', 'representante_temuco.json'),
]

for slug, json_file in json_configs:
    assistant = AIAssistant.objects.filter(slug=slug).first()
    if assistant and assistant.chunks.count() == 0:
        print(f"📚 Base de datos de vectores vacía para {assistant.name}. Iniciando ingesta desde {json_file}...")
        
        json_path = os.path.join(settings.BASE_DIR, 'ai_modules', 'knowledge_base', json_file)
        if not os.path.exists(json_path):
            print(f"  ⚠️  Archivo {json_file} no encontrado en path: {json_path}")
            continue

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Manejar diferentes estructuras de JSON (utp es lista, representante es dict con key 'chunks')
            chunks_data = data.get('chunks', []) if isinstance(data, dict) else data

        if not chunks_data:
            print(f"  ⚠️  No se encontraron fragmentos en {json_file}")
            continue

        print(f"  -> Procesando {len(chunks_data)} fragmentos...")

        import openai
        import uuid
        from ai_modules.models import AIKnowledgeChunk
        
        api_key_val = getattr(settings, 'OPENAI_API_KEY', os.environ.get('OPENAI_API_KEY'))
        if not api_key_val:
            print("  ❌ Error: OPENAI_API_KEY no encontrada.")
            continue
            
        client = openai.OpenAI(api_key=api_key_val)
        doc_counters = {}
        chunks_batch = []
        texts_batch = []
        batch_size = 100 
        session_id = uuid.uuid4().hex[:6]

        for i, item in enumerate(chunks_data):
            # Normalizar acceso a contenido entre versiones de JSON
            text_content = item.get('text_content') or item.get('texto_contenido', '')
            if not text_content: continue

            # Normalizar metadatos
            metadata = item.get('legal_metadata') or item.get('metadatos', {})
            doc_name = metadata.get('source_file') or metadata.get('fuente_archivo', 'Desconocido')
            
            if doc_name not in doc_counters:
                doc_counters[doc_name] = 0
            
            chunk = AIKnowledgeChunk(
                assistant=assistant,
                content=text_content,
                metadata=json.dumps(metadata),
                chunk_id=f"{slug[:4]}_{session_id}_{i}",
                document_name=doc_name,
                index=doc_counters[doc_name]
            )
            chunks_batch.append(chunk)
            texts_batch.append(text_content)
            doc_counters[doc_name] += 1

            if len(texts_batch) == batch_size or i == len(chunks_data) - 1:
                try:
                    response = client.embeddings.create(input=texts_batch, model="text-embedding-3-small")
                    for j, emb_data in enumerate(response.data):
                        chunks_batch[j].embedding = json.dumps(emb_data.embedding)
                    AIKnowledgeChunk.objects.bulk_create(chunks_batch)
                except Exception as e:
                    print(f"  ❌ Error en embeddings batch: {e}")
                chunks_batch, texts_batch = [], []

        print(f"  ✅ {assistant.name} vectorizado correctamente.")

print("\n🚀 MEGA-SEED completado con éxito.")
print("💡 Tip: Para probar, usa p.ej. 'utp.temuco' / 'Admin1234!'")
