import json
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from ai_modules.models import AIAssistant, AIKnowledgeChunk

class Command(BaseCommand):
    help = 'Configura el asistente UTP Temuco e ingesta su base de conocimientos JSON'

    def handle(self, *args, **options):
        json_path = os.path.join(settings.BASE_DIR, 'ai_modules', 'knowledge_base', 'utp_temuco.json')
        assistant_slug = 'utp-temuco'

        # 1. Obtener o crear el asistente
        assistant, created = AIAssistant.objects.get_or_create(
            slug=assistant_slug,
            defaults={
                'name': 'UTP Temuco (San Francisco de Asís)',
                'profile_role': 'utp',
                'establishment': 'temuco',
                'image_name': 'utp_avatar.png',
                'is_chat_enabled': True
            }
        )

        # 2. Actualizar el Prompt Maestro
        system_instruction = (
            "Eres el asistente oficial de la UTP de la Escuela San Francisco de Asís en Temuco. "
            "Tu función es tomar decisiones respecto del proceso de enseñanza y aprendizaje, siempre velando "
            "por el bienestar superior del estudiante, considerando las políticas educativas, las leyes y decretos "
            "de educación, nuestro PEI y nuestros reglamentos internos.\n\n"
            "Siempre desde una mirada formadora, emite un análisis del caso planteado por el usuario. "
            "Para fundamentar tu respuesta, utiliza EXCLUSIVAMENTE los fragmentos de normativa y reglamentos "
            "proporcionados en el 'CONTEXTO DE DOCUMENTOS RELEVANTES' a continuación.\n\n"
            "Tu respuesta DEBE cubrir al menos estos 6 puntos estructurados:\n"
            "1. Análisis del caso con una mirada desde la articulación de la normativa vigente, PEI, RICE y reglamento de evaluación.\n"
            "2. Propuesta concreta para evaluación/calificación.\n"
            "3. Medidas formativas específicas para el estudiante.\n"
            "4. Medidas para la comunidad docente que permitan prevenir futuras situaciones similares.\n"
            "5. Vinculación con la familia.\n"
            "6. Ruta de blindaje para futuras denuncias en la Superintendencia de Educación.\n\n"
            "Si el contexto no contiene información suficiente para responder alguno de los puntos, indícalo "
            "basándote en que no se encuentra en la normativa actual. Mantén un tono profesional, empático y decisivo."
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

        self.stdout.write(f'Iniciando ingesta y generación de embeddings para {len(data)} fragmentos...')
        
        # Necesitamos openai para esta fase inicial (una sola vez)
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

        for i, item in enumerate(data):
            doc_name = item['metadatos'].get('fuente_archivo', 'Desconocido')
            if doc_name not in doc_counters:
                doc_counters[doc_name] = 0
            
            chunk = AIKnowledgeChunk(
                assistant=assistant,
                content=item['texto_contenido'],
                metadata=item['metadatos'],
                chunk_id=item['metadatos']['chunk_id'],
                document_name=doc_name,
                index=doc_counters[doc_name]
            )
            chunks_batch.append(chunk)
            texts_batch.append(item['texto_contenido'])
            doc_counters[doc_name] += 1

            # Procesar en lotes
            if len(texts_batch) == batch_size or i == len(data) - 1:
                self.stdout.write(f'Generando embeddings {i+1-len(texts_batch)} al {i+1}...')
                try:
                    response = client.embeddings.create(
                        input=texts_batch,
                        model="text-embedding-3-small"
                    )
                    for j, emb_data in enumerate(response.data):
                        chunks_batch[j].embedding = emb_data.embedding
                    
                    # Guardar masivamente en BD
                    AIKnowledgeChunk.objects.bulk_create(chunks_batch)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error en embeddings: {e}'))
                
                # Resetear lote
                chunks_batch = []
                texts_batch = []
        
        self.stdout.write(self.style.SUCCESS(f'Ingesta vectorizada completada. {len(data)} registros creados.'))
