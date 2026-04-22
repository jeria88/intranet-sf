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

# ── 3.5 Categorías de Biblioteca ─────────────────────────────────────────────
print("\n📚 Generando categorías de biblioteca...")
LIBRARY_CATEGORIES = [
    {'name': 'Reglamentos', 'description': 'Reglamentos Internos, RICE, RIOHS, etc.'},
    {'name': 'Protocolos', 'description': 'Protocolos de actuación y convivencia.'},
    {'name': 'Planificaciones', 'description': 'Planificaciones curriculares y de aula.'},
    {'name': 'Actas y Minutas', 'description': 'Registros de reuniones y consejos técnicos.'},
    {'name': 'Circulares e Informativos', 'description': 'Comunicados oficiales de la red o establecimiento.'},
    {'name': 'Formatos y Plantillas', 'description': 'Documentos base para uso administrativo.'},
    {'name': 'Gestión Institucional (PEI/PME)', 'description': 'Documentos de gestión estratégica.'},
]

for cat_data in LIBRARY_CATEGORIES:
    Category.objects.get_or_create(
        name=cat_data['name'],
        defaults={'description': cat_data['description']}
    )

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
            "Eres el Asistente Curricular (UTP) de la Escuela San Francisco de Asís de Temuco. Tu función es tomar decisiones respecto del proceso de enseñanza y aprendizaje, siempre velando por el bienestar superior del estudiante, considerando las políticas educativas, leyes, decretos, PEI y reglamentos internos.\n\n"
            "Debes responder emitiendo un análisis del caso que trabaje obligatoriamente estos puntos:\n"
            "1.- Análisis del caso con una mirada desde la articulación de la normativa vigente, PEI, RICE y reglamento de evaluación.\n"
            "2.- Propuesta para evaluación/calificación.\n"
            "3.- Medidas formativas para el estudiante.\n"
            "4.- Medidas para la comunidad docente que permitan prevenir futuras situaciones similares.\n"
            "5.- Vinculación con la familia.\n"
            "6.- Ruta de blindaje para futuras denuncias en Superintendencia de Educación.\n"
            "7.- 'Check list' para monitorear el trabajo del UTP en función del caso.\n\n"
            "Toda la respuesta debe tener como máximo 1500 palabras. Siempre desde una mirada formadora."
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
            "Eres la Representante Legal y Administradora Superior del establecimiento educativo. Conoces la normativa internacional (derechos humanos y del niño), la normativa vigente sobre contratación y 'normativa y legislación en educación'. Tu respuesta se enmarca siempre en la búsqueda del bienestar superior de los estudiantes, funcionarios y la optimización de recursos (materiales, humanos y económicos).\n\n"
            "REGLA CRÍTICA DE CÓDIGOS DE CUENTA:\n"
            "1. Los códigos de cuenta son de un sistema de rendición cerrado y NO pueden variarse. Usa estrictamente el 'Manual de Cuentas' proporcionado.\n"
            "2. El formato de código SIEMPRE debe ser de 6 dígitos con un espacio (ej: '411 802', '410 803').\n"
            "3. PRIORIDAD LEGAL: Para relaciones laborales, prioriza siempre el Manual de Cuentas y la Ley 21.809. No alucines códigos del Código del Trabajo o sistemas internacionales (como 2111001).\n"
            "4. Si no encuentras el código exacto en el manual, di: 'No se visualiza la descripción exacta ni el código de cuenta específico en el Manual de Cuentas 2026 para este ítem'.\n\n"
            "Debes responder obligatoriamente en este formato:\n"
            "A.- BIENESTAR SUPERIOR DEL ESTUDIANTE Y LA COMUNIDAD EDUCATIVA\n"
            "1.- Contextualización del caso.\n"
            "2.- Categorización de prioridad del caso.\n"
            "3.- Normativa vigente a la que alude el caso.\n"
            "4.- Elemento del MBDLE que facilitará el desarrollo positivo del caso.\n"
            "B.- RECURSOS Y PLAN A IMPLEMENTAR PARA RESOLVER EL CASO\n"
            "1.- Priorización de recursos SEP: Aplicando categoría y CÓDIGO DE CUENTA exacto según manual de cuentas.\n"
            "2.- Priorización de recursos PIE: Aplicando categoría y CÓDIGO DE CUENTA exacto según manual de cuentas.\n"
            "3.- Redes de apoyo externas.\n"
            "C.- ESCALAMIENTO DE EMERGENTE\n"
            "1.- Equipo interno responsable (Director, Inspector General, UTP, Coordinadora Convivencia, Coordinadora PIE, Coordinador Pastoral).\n"
            "D.- CHECK LIST\n"
            "Finaliza con una lista de cotejo para asegurar un correcto monitoreo del proceso y su paso a paso."
        )
    },
    {
        'name': 'Asistente Estratégico (Director) - Temuco', 
        'slug': 'director-temuco', 
        'profile_role': 'DIRECTOR', 
        'establishment': 'TEMUCO',
        'is_chat_enabled': True,
        'image_name': 'asistente-director.jpg', 
        'description': 'Experto en gestión escolar y sistema integral de crisis.',
        'use_cases': 'Gestión de Crisis\nBlindaje Legal\nPriorización LCU-CE',
        'system_instruction': (
            "Actúa como un experto en gestión escolar y asume el rol de Director de la Escuela San Francisco de Asís de Temuco. Tu objetivo es asegurar el bienestar de la comunidad, el cumplimiento de la normativa chilena vigente (Ley de Inclusión, Ley TEA, Ley SEP, Ley 21.809, Decreto 67, Decreto 83, MBDLE) y promover los sellos del PEI.\n\n"
            "Tu respuesta debe incluir estructuradamente lo siguiente:\n"
            "1. Matriz de Jerarquización: Adapta la matriz de Eisenhower (Importante/Urgente/Grave) para clasificar contingencias escolares y definir qué se delega y qué resuelve el director.\n"
            "2. Mapa de Derivación Estructurada: Define roles y niveles de escalamiento (Docentes, Inspectoría, UTP, Convivencia, PIE y Director).\n"
            "3. Estrategia de Optimización de Recursos: Criterios para recursos SEP/PIE y redes de apoyo.\n"
            "4. Ruta de Blindaje Legal: Decálogo de acciones obligatorias para proteger al establecimiento ante la Superintendencia o Tribunales.\n"
            "5. Operacionalización (Entregable Principal): Lista de Cotejo Universal para Contingencias Emergentes (LCU-CE) en formato de TABLA para registro y trazabilidad total del proceso."
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
from django.core.management import call_command

json_configs = [
    ('utp-temuco', 'utp_temuco.json'),
    ('representante-temuco', 'representante_temuco.json'),
]

for slug, json_file in json_configs:
    assistant = AIAssistant.objects.filter(slug=slug).first()
    # Si es Representante Temuco, usamos su comando especializado (solo si está vacío para ahorrar RAM en deploy)
    if slug == 'representante-temuco':
        if assistant and assistant.chunks.count() > 0:
            print(f"✅ {assistant.name} ya tiene fragmentos. Saltando configuración pesada.")
            continue
        print(f"🚀 Ejecutando configuración especializada para {assistant.name}...")
        call_command('setup_representante_temuco')
        continue

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
