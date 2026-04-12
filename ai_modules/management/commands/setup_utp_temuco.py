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

        self.stdout.write(f'Iniciando ingesta de {len(data)} fragmentos...')
        
        # Limpiar chunks previos para evitar duplicados si se re-ejecuta
        assistant.chunks.all().delete()

        chunks_to_create = []
        doc_counters = {} # Para llevar el índice por documento

        for item in data:
            doc_name = item['metadatos'].get('fuente_archivo', 'Desconocido')
            if doc_name not in doc_counters:
                doc_counters[doc_name] = 0
            
            chunks_to_create.append(AIKnowledgeChunk(
                assistant=assistant,
                content=item['texto_contenido'],
                metadata=item['metadatos'],
                chunk_id=item['metadatos']['chunk_id'],
                document_name=doc_name,
                index=doc_counters[doc_name]
            ))
            doc_counters[doc_name] += 1

        # Creación masiva para eficiencia
        AIKnowledgeChunk.objects.bulk_create(chunks_to_create)
        
        self.stdout.write(self.style.SUCCESS(f'Ingesta completada. {len(chunks_to_create)} registros creados.'))
