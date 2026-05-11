import os
from django.core.management.base import BaseCommand
from django.conf import settings


DOCS = [
    {'nombre': 'Metodología SIMCE',           'archivo': 'metodologia_simce.pdf',      'asignatura': 'general'},
    {'nombre': 'Ejemplos Básica',             'archivo': 'ejemplos_basica.pdf',         'asignatura': 'general'},
    {'nombre': 'Ejemplos Media',              'archivo': 'ejemplos_media.pdf',          'asignatura': 'general'},
    {'nombre': 'Niveles de Logro 4° Básico',  'archivo': 'niveles_logro_4basico.pdf',   'asignatura': 'general'},
]


class Command(BaseCommand):
    help = 'Indexa los PDFs de simce_docs/ como chunks con embeddings para el RAG SIMCE'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Re-indexar aunque ya estén procesados')

    def handle(self, *args, **options):
        from simce.models import SimceDocumento
        from simce.rag import indexar_documento

        docs_dir = os.path.join(settings.BASE_DIR, 'simce_docs')
        force = options['force']

        for info in DOCS:
            file_path = os.path.join(docs_dir, info['archivo'])
            if not os.path.exists(file_path):
                self.stdout.write(self.style.WARNING(f"  Archivo no encontrado: {info['archivo']}"))
                continue

            doc, created = SimceDocumento.objects.get_or_create(
                nombre=info['nombre'],
                defaults={
                    'asignatura': info['asignatura'],
                    'file_path': file_path,
                },
            )
            if not created:
                doc.file_path = file_path
                doc.save(update_fields=['file_path'])

            if doc.procesado and not force:
                self.stdout.write(f"  ✓ Ya procesado: {info['nombre']} ({doc.n_chunks} chunks)")
                continue

            self.stdout.write(f"  Indexando: {info['nombre']}…")
            ok = indexar_documento(doc)
            if ok:
                self.stdout.write(self.style.SUCCESS(f"  ✓ {info['nombre']}: {doc.n_chunks} chunks"))
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Error indexando {info['nombre']}"))

        self.stdout.write(self.style.SUCCESS('index_simce_docs completado.'))
