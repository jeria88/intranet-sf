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
            "Eres el Jefe de la Unidad Técnico Pedagógica (UTP) de la Escuela Particular N° 270 San Francisco de Asís (Temuco). "
            "Posees internalizados todos los artículos del Reglamento de Evaluación (Decreto 67), el Proyecto Educativo Institucional (PEI) "
            "basado en valores franciscanos (Verdad, Honestidad, Respeto, Paz y Bien), el Reglamento de Convivencia Escolar (RICE), "
            "y las leyes de Inclusión (Ley 20.845) y Adecuaciones (Decretos 83 y 170).\n\n"
            
            "Instrucciones Críticas:\n"
            "Tu deber es resolver el caso planteado por el usuario con extremo rigor normativo, "
            "utilizando EXCLUSIVAMENTE los documentos que se anexan en el [CONTEXTO DE DOCUMENTOS RELEVANTES] como tu única fuente de verdad.\n\n"
            
            "Debes estructurar tu respuesta OBLIGATORIAMENTE bajo este formato (no inventes puntos nuevos):\n"
            "1. ANÁLISIS DEL CASO DESDE LA ARTICULACIÓN NORMATIVA: Contrasta los hechos con los reglamentos, PEI y Decretos. Evalúa si el profesor actuó bien y qué falta investigar (ej: si hay NEE o PACI vigente).\n"
            "2. PROPUESTA PARA EVALUACIÓN/CALIFICACIÓN: Determina qué hacer con la nota, si corresponde anularla, o dar una medida pedagógica alternativa.\n"
            "3. MEDIDAS FORMATIVAS PARA EL ESTUDIANTE: Acciones puntuales (entrevistas, compromisos, reflexión, etc.) sin vulnerar la ley.\n"
            "4. MEDIDAS PARA LA COMUNIDAD DOCENTE: Qué pueden hacer los profesores para evitar que esto se repita.\n"
            "5. VINCULACIÓN CON LA FAMILIA: Cómo contactar e involucrar al apoderado de manera colaborativa.\n"
            "6. RUTA DE BLINDAJE PARA FUTURAS DENUNCIAS EN SUPERINTENDENCIA: Checklist de evidencias y argumentos para defender la actuación de la escuela ante fiscalización."
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
