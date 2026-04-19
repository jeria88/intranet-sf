import json
import os
import uuid
from django.core.management.base import BaseCommand
from ai_modules.models import AIAssistant, AIKnowledgeChunk
from ai_modules.utils import get_openai_embedding
from django.conf import settings
from django.db import connections

class Command(BaseCommand):
    help = 'Sincroniza la base de conocimientos JSON hacia la base de datos de Supabase'

    def add_arguments(self, parser):
        parser.add_argument('--assistant', type=str, required=True, help='Slug del asistente (utp-temuco o representante-temuco)')
        parser.add_argument('--json', type=str, required=True, help='Nombre del archivo JSON en knowledge_base/')

    def handle(self, *args, **options):
        assistant_slug = options['assistant']
        json_filename = options['json']
        json_path = os.path.join(settings.BASE_DIR, 'ai_modules', 'knowledge_base', json_filename)
        
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'No se encontró el archivo {json_path}'))
            return

        assistant = AIAssistant.objects.get(slug=assistant_slug)
        self.stdout.write(self.style.SUCCESS(f'Iniciando sincronización para {assistant.name} hacia Supabase...'))

        # 1. Cargar el JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # El formato varía entre utp (lista) y representante (dict con 'chunks')
            chunks = data if isinstance(data, list) else data.get('chunks', [])

        total = len(chunks)
        self.stdout.write(self.style.NOTICE(f'Procesando {total} fragmentos...'))
        
        # 2. Limpiar chunks previos en la base de datos de conocimiento
        AIKnowledgeChunk.objects.using('knowledge_base').filter(assistant=assistant).delete()

        count = 0
        batch_size = 50
        batch = []

        for index, item in enumerate(chunks): 
            # Adaptación de campos según el origen
            if 'texto_contenido' in item: # Formato UTP
                text = item['texto_contenido']
                metadata = item['metadatos']
                c_id = metadata.get('chunk_id', f"sync_{index}")
                doc_name = metadata.get('fuente_archivo', 'desconocido')
            else: # Formato Representante
                text = item.get('text_content', '')
                metadata = item.get('legal_metadata', {})
                c_id = f"rep_{uuid.uuid4().hex[:8]}_{index}"
                doc_name = metadata.get('source_file', 'desconocido')

            if not text: continue
                
            # IMPORTANTE: Aquí generamos el embedding si no existe
            # Para una migración masiva, lo ideal es usar el batch de OpenAI
            embedding = get_openai_embedding(text)
            
            chunk = AIKnowledgeChunk(
                assistant=assistant,
                content=text,
                embedding=json.dumps(embedding) if embedding else None,
                metadata=metadata,
                chunk_id=c_id,
                document_name=doc_name,
                index=index
            )
            batch.append(chunk)
            
            if len(batch) >= batch_size:
                AIKnowledgeChunk.objects.using('knowledge_base').bulk_create(batch)
                batch = []
                count += batch_size
                self.stdout.write(f'Sincronizados {count}/{total}...')

        if batch:
            AIKnowledgeChunk.objects.using('knowledge_base').bulk_create(batch)
            count += len(batch)

        self.stdout.write(self.style.SUCCESS(f'ÉXITO: {count} fragmentos subidos a Supabase.'))
