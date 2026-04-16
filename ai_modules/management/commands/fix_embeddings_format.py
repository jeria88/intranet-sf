import json
from django.core.management.base import BaseCommand
from ai_modules.models import AIKnowledgeChunk

class Command(BaseCommand):
    help = 'Corrige el formato de embeddings y metadatos en la base de datos (des-serializa strings JSON)'

    def handle(self, *args, **options):
        # Usar iterator() para no cargar todo a la vez en RAM
        chunks = AIKnowledgeChunk.objects.all().iterator(chunk_size=1000)
        
        batch = []
        batch_size = 500
        processed_count = 0
        updated_count = 0

        self.stdout.write('Iniciando corrección de formato...')

        for chunk in chunks:
            modified = False
            
            # Corregir embedding si es un string
            if isinstance(chunk.embedding, str):
                try:
                    chunk.embedding = json.loads(chunk.embedding)
                    modified = True
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error al parsear embedding en chunk {chunk.id}: {e}'))

            # Corregir metadata si es un string
            if isinstance(chunk.metadata, str):
                try:
                    chunk.metadata = json.loads(chunk.metadata)
                    modified = True
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error al parsear metadata en chunk {chunk.id}: {e}'))

            if modified:
                batch.append(chunk)
                updated_count += 1

            processed_count += 1

            if len(batch) >= batch_size:
                AIKnowledgeChunk.objects.bulk_update(batch, ['embedding', 'metadata'])
                self.stdout.write(f'Actualizados {processed_count} fragmentos...')
                batch = []

        # Lote final
        if batch:
            AIKnowledgeChunk.objects.bulk_update(batch, ['embedding', 'metadata'])

        self.stdout.write(self.style.SUCCESS(f'Finalizado. Se actualizaron {updated_count} de {processed_count} fragmentos.'))
