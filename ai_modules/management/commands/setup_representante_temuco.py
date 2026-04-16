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
        assistant.system_instruction = system_instruction
        assistant.save()
        self.stdout.write(self.style.SUCCESS(f'Prompt del asistente "{assistant.slug}" actualizado.'))

        # 3. Ingesta de Chunks
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'Archivo JSON no encontrado en: {json_path}'))
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            chunks_data = data.get('chunks', [])

        total_chunks = len(chunks_data)
        self.stdout.write(f'Iniciando ingesta y generación de embeddings para {total_chunks} fragmentos...')
        
        # Necesitamos openai para esta fase inicial
        import openai
        api_key_val = getattr(settings, 'OPENAI_API_KEY', os.environ.get('OPENAI_API_KEY'))
        if not api_key_val:
            self.stdout.write(self.style.ERROR('OPENAI_API_KEY no encontrada. No se pueden generar embeddings.'))
            return
            
        client = openai.OpenAI(api_key=api_key_val)

        assistant.chunks.all().delete()

        doc_counters = {}
        chunks_batch = []
        texts_batch = []
        batch_size = 100 # OpenAI soporta varios inputs a la vez
        
        # Usamos UUID corto para evitar identificadores repetidos en la BD de Chroma u otros si aplican
        session_id = uuid.uuid4().hex[:8]

        for i, item in enumerate(chunks_data):
            text_content = item.get('text_content', '')
            if not text_content:
                continue

            metadata = item.get('legal_metadata', {})
            doc_name = metadata.get('source_file', 'representante_temuco.json')
            
            if doc_name not in doc_counters:
                doc_counters[doc_name] = 0
            
            chunk = AIKnowledgeChunk(
                assistant=assistant,
                content=text_content,
                metadata=json.dumps(metadata),
                chunk_id=f"rep_tem_{session_id}_{i}",
                document_name=doc_name,
                index=doc_counters[doc_name]
            )
            chunks_batch.append(chunk)
            texts_batch.append(text_content)
            doc_counters[doc_name] += 1

            # Procesar en lotes
            if len(texts_batch) == batch_size or i == total_chunks - 1:
                self.stdout.write(f'Generando embeddings {i+1-len(texts_batch)} al {i+1} de {total_chunks}...')
                try:
                    response = client.embeddings.create(
                        input=texts_batch,
                        model="text-embedding-3-small"
                    )
                    for j, emb_data in enumerate(response.data):
                        # Convert list of floats to JSON array string
                        chunks_batch[j].embedding = json.dumps(emb_data.embedding)
                    
                    # Guardar masivamente en BD
                    AIKnowledgeChunk.objects.bulk_create(chunks_batch)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error en embeddings: {e}'))
                
                # Resetear lote
                chunks_batch = []
                texts_batch = []
        
        self.stdout.write(self.style.SUCCESS(f'Ingesta vectorizada completada. {total_chunks} fragmentos procesados.'))
