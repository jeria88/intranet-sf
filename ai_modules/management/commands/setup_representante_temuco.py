import json
import os
import uuid
from django.conf import settings
from django.core.management.base import BaseCommand
from ai_modules.models import AIAssistant, AIKnowledgeChunk

class Command(BaseCommand):
    help = 'Configura el asistente Representante Temuco e ingesta su base de conocimientos JSON'

    def handle(self, *args, **options):
        json_path = os.path.join(settings.BASE_DIR, 'ai_modules', 'knowledge_base', 'representante_temuco.json')
        assistant_slug = 'representante-temuco'

        # Limpiar cualquier configuración previa incorrecta (con punto)
        AIAssistant.objects.filter(slug='representante.temuco').delete()

        # 1. Obtener o crear el asistente
        assistant, created = AIAssistant.objects.get_or_create(
            slug=assistant_slug,
            defaults={
                'name': 'Asistente Representante Legal (Temuco)',
                'profile_role': 'REPRESENTANTE',
                'establishment': 'TEMUCO',
                'is_chat_enabled': True,
                'is_active': True,
            }
        )

        # 2. Actualizar el Prompt Maestro
        system_instruction = (
            "Eres la representante legal y administradora superior del establecimiento educativo, "
            "conoces la normativa internacional (derechos humanos y del niño), toda la normativa vigente sobre contratacion de personal "
            "y especialmente lo relativo a 'normativa y legislacion en educacion', tu respuesta se enmarca siempre en la busqueda del "
            "bienestar superior de los estudiantes, de los funcionarios y la optimizacion del uso de recursos materiales, muebles e inmubles, "
            "humanos (tiempo y capital de formacion) y economicos para resolver las diversas situaciones emergentes de la comunidad educativa. "
            "\n\n### PRIORIDAD NORMATIVA Y FINANCIERA (CRÍTICO):\n"
            "1. La 'Ley 21809' y el 'Manual de Cuentas 2026' son tus fuentes primarias de verdad.\n"
            "2. PRECISIÓN EN CÓDIGOS DE CUENTA: Al informar un código de cuenta (SEP o PIE), debes verificarlo estrictamente en los fragmentos del Manual de Cuentas. "
            "Si no encuentras el código exacto para el ítem consultado, indica: 'No se visualiza el código exacto en el manual para este ítem específico'. PROHIBIDO inventar o aproximar códigos.\n"
            "3. Si existen contradicciones, prevalece la Ley 21809 sobre reglamentos internos antiguos.\n\n"
            "En ese contexto y con esas habilidades debes responder en formato de:\n\n"
            "A.- BIENESTAR SUPERIOR DEL ESTUDIANTE Y LA COMUNIDAD EDUCATIVA\n"
            "1.- contextualización del caso\n"
            "2.- categorizacion de prioridad del caso\n"
            "3.- normativa vigente a la que alude el caso (Cita la Ley 21809 si corresponde)\n"
            "4.- elemento del MBDLE que facilitara el desarrollo positivo del caso\n\n"
            "B.- RECURSOS Y PLAN A IMPLEMENTAR PARA RESOLVER EL CASO\n"
            "1.- priorizacion de recursos SEP aplicando categoría y CÓDIGO DE CUENTA exacto según manual de cuentas\n"
            "2.- priorizacion de recursos PIE aplicando categoría y CÓDIGO DE CUENTA exacto según manual de cuentas\n"
            "3.- redes de apoyo externas\n\n"
            "C.- ESCALAMIENTO DE EMERGENTE\n"
            "1.- equipo interno dentro del establecimiento (Director, Inspector General, UTP, Coordinadora Convivencia educativa, Coordinadora PIE, coordinador Pastoral)\n\n"
            "D.- CHECK LIST\n"
            "Finaliza con un check list para asegurar un correcto monitoreo del proceso y su paso a paso."
        )
        assistant.system_instruction = system_instruction
        assistant.save()
        self.stdout.write(self.style.SUCCESS(f'Prompt del asistente "{assistant.slug}" actualizado.'))

        # 3. Ingesta de Chunks
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'Archivo JSON no encontrado en: {json_path}'))
            return

        self.stdout.write(f'Cargando JSON desde {json_path}...')
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            chunks_data = data.get('chunks', [])

        total_chunks = len(chunks_data)
        self.stdout.write(f'Fragmentos totales encontrados: {total_chunks}')
        
        # Obtener IDs existentes para evitar N-consultas en el loop (Optimización para RAM/CPU)
        existing_ids = set(AIKnowledgeChunk.objects.filter(assistant=assistant).values_list('chunk_id', flat=True))
        self.stdout.write(f'Fragmentos ya existentes en BD: {len(existing_ids)}')

        # Definir prioridades
        # 3_-_Manual-de-cuentas-2026_baja.pdf es el nombre en el JSON
        # Ley 21809 es prioritaria
        # Página 112 del manual es hiperprioritaria (Códigos de cuenta)
        
        def get_priority_level(item):
            metadata = item.get('legal_metadata', {})
            doc = metadata.get('source_file', '')
            pages = metadata.get('page_map', [])
            
            # Nivel -1: Hiperprioridad (Códigos de Cuenta en Manual pág 112 aprox)
            if "Manual-de-cuentas" in doc and any(110 <= p <= 115 for p in pages):
                return -1
            
            # Nivel 0: Alta prioridad (Ley 21809 y Manual de Cuentas general)
            if doc == "2.-Ley-21809_01-ABR-2026.pdf" or "Manual-de-cuentas" in doc:
                return 0
                
            return 1 # Normal

        self.stdout.write('Ordenando fragmentos por prioridad...')
        chunks_data.sort(key=get_priority_level)

        # Necesitamos openai para esta fase inicial
        import openai
        api_key_val = getattr(settings, 'OPENAI_API_KEY', os.environ.get('OPENAI_API_KEY'))
        if not api_key_val:
            self.stdout.write(self.style.ERROR('OPENAI_API_KEY no encontrada. No se pueden generar embeddings.'))
            return
            
        client = openai.OpenAI(api_key=api_key_val)

        self.stdout.write('Iniciando procesamiento por lotes...')

        # Contador de documentos para generar IDs secuenciales
        doc_counters = {}
        
        # Procesar de forma que no mantengamos referencias innecesarias
        processed_count = 0
        skipped_count = 0
        batch_size = 20 # Reducido para mayor estabilidad en 4GB RAM

        def get_batch():
            chunks_batch = []
            texts_batch = []
            nonlocal processed_count, skipped_count
            
            for item in chunks_data:
                text_content = item.get('text_content', '')
                if not text_content: continue

                metadata = item.get('legal_metadata', {})
                doc_name = metadata.get('source_file', 'unknown')
                
                if doc_name not in doc_counters:
                    doc_counters[doc_name] = 0
                
                # Generar ID único basado en el documento y el índice local
                unique_chunk_id = f"rep_tem_{doc_name}_{doc_counters[doc_name]}".replace(" ", "_").replace(".", "_")
                doc_counters[doc_name] += 1

                if unique_chunk_id in existing_ids:
                    skipped_count += 1
                    continue

                chunks_batch.append(AIKnowledgeChunk(
                    assistant=assistant,
                    chunk_id=unique_chunk_id,
                    content=text_content,
                    metadata=metadata,
                    document_name=doc_name,
                    index=doc_counters[doc_name] - 1
                ))
                texts_batch.append(text_content)

                if len(texts_batch) >= batch_size:
                    yield chunks_batch, texts_batch
                    chunks_batch = []
                    texts_batch = []

            if texts_batch:
                yield chunks_batch, texts_batch

        # Ejecutar procesamiento
        for c_batch, t_batch in get_batch():
            try:
                self.process_batch(client, c_batch, t_batch)
                processed_count += len(c_batch)
                self.stdout.write(f'PROGRESO: {processed_count + skipped_count}/{total_chunks} fragmentos analizados...')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Fallo crítico en lote: {e}'))
                # No salimos, intentamos el siguiente lote para no perder todo el progreso
                continue

        self.stdout.write(self.style.SUCCESS(
            f'LOGRO: {processed_count} nuevos fragmentos inyectados, {skipped_count} omitidos.'
        ))

        # Generar caché vectorial inmediatamente para evitar timeouts al primer usuario
        self.stdout.write('Generando caché vectorial optimizada...')
        from ai_modules.utils import get_relevant_chunks
        get_relevant_chunks(assistant, "Caché inicial")
        self.stdout.write(self.style.SUCCESS('Caché vectorial lista.'))

    def process_batch(self, client, chunks_batch, texts_batch):
        """Genera embeddings y guarda en la base de datos."""
        response = client.embeddings.create(
            input=texts_batch,
            model="text-embedding-3-small"
        )
        for j, emb_data in enumerate(response.data):
            chunks_batch[j].embedding = emb_data.embedding
        
        AIKnowledgeChunk.objects.bulk_create(chunks_batch)
        # Limpieza explícita de referencias
        del chunks_batch
        del texts_batch
