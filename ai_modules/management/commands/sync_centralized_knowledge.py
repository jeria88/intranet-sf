import json
import os
import uuid
import gc
from django.core.management.base import BaseCommand
from ai_modules.models import AIAssistant, AIKnowledgeChunk
from ai_modules.utils import get_openai_embedding
from django.conf import settings

class Command(BaseCommand):
    help = 'Sincroniza la base de conocimientos CENTRALIZADA hacia Supabase con optimización de RAM'

    def add_arguments(self, parser):
        parser.add_argument('--resume', type=int, default=0, help='Índice desde el cual reanudar')

    def handle(self, *args, **options):
        json_path = os.path.join(settings.BASE_DIR, 'ai_modules', 'knowledge_base', 'base_conocimientos_supabase.json')
        resume_index = options['resume']
        
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'No se encontró el archivo {json_path}'))
            return

        assistant = AIAssistant.objects.get(slug='global-knowledge')
        self.stdout.write(self.style.SUCCESS(f'Reanudando sincronización CENTRALIZADA desde índice {resume_index}...'))

        # Para ahorrar RAM, no cargamos todo el JSON de una vez si es posible, 
        # pero JSON.load necesita el archivo completo. Usaremos gc.collect() agresivo.
        with open(json_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)

        total = len(chunks)
        self.stdout.write(self.style.NOTICE(f'Total de fragmentos en archivo: {total}'))
        
        if resume_index == 0:
            self.stdout.write(self.style.WARNING('Limpiando base de datos previa...'))
            AIKnowledgeChunk.objects.using('knowledge_base').filter(assistant=assistant).delete()

        count = resume_index
        batch_size = 25 # Reducido para ahorrar RAM
        batch = []

        # Solo iteramos sobre lo que falta
        for index in range(resume_index, total):
            item = chunks[index]
            text = item.get('texto_contenido', '')
            metadata = item.get('metadatos', {})
            
            if not text: continue
                
            embedding = get_openai_embedding(text)
            
            chunk = AIKnowledgeChunk(
                assistant=assistant,
                content=text,
                embedding=json.dumps(embedding) if embedding else None,
                metadata=metadata,
                chunk_id=f"global_{uuid.uuid4().hex[:8]}_{index}",
                document_name=metadata.get('fuente', 'centralizado'),
                index=index
            )
            batch.append(chunk)
            
            if len(batch) >= batch_size:
                AIKnowledgeChunk.objects.using('knowledge_base').bulk_create(batch)
                batch = []
                count += batch_size
                self.stdout.write(f'PROGRESO: {count}/{total} ({(count/total)*100:.1f}%)')
                # Liberar memoria explícitamente
                gc.collect()

        if batch:
            AIKnowledgeChunk.objects.using('knowledge_base').bulk_create(batch)
            count += len(batch)

        self.stdout.write(self.style.SUCCESS(f'ÉXITO: Sincronización completada hasta el final ({count} fragmentos).'))
