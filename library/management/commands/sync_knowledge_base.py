import os
import boto3
from django.core.management.base import BaseCommand
from django.conf import settings
from library.models import Category, Document
from users.models import User

class Command(BaseCommand):
    help = 'Sincroniza documentos de la base de conocimientos desde Cloudflare R2'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando sincronización desde Cloudflare R2...")
        
        # Conexión a R2
        try:
            s3 = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                region_name='auto'
            )
        except Exception as e:
            self.stderr.write(f"Error conectando a R2: {e}")
            return

        base_path = 'documents/2026/04/22/base-conocimientos/'
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        prefix = 'media/' + base_path
        
        self.stdout.write(f"Listando archivos en {bucket}/{prefix}...")
        
        files = []
        try:
            paginator = s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        if not key.endswith('/'):
                            # Ruta relativa a la raíz de almacenamiento (sin 'media/')
                            rel_path = key.replace('media/', '', 1)
                            files.append(rel_path)
        except Exception as e:
            self.stderr.write(f"Error listando archivos: {e}")
            return

        if not files:
            self.stdout.write("No se encontraron archivos para procesar.")
            return

        # Obtener o crear categoría
        category, created = Category.objects.get_or_create(
            name='Base de Conocimientos',
            defaults={'description': 'Documentos y procedimientos del equipo directivo.'}
        )
        if created:
            self.stdout.write(f"Categoría creada: {category.name}")

        # Autor (admin o primer superusuario)
        author = User.objects.filter(is_superuser=True).first() or User.objects.first()

        count = 0
        for full_path in files:
            filename = os.path.basename(full_path)
            name_no_ext = os.path.splitext(filename)[0]
            # Limpiar título
            title = name_no_ext.replace('-', ' ').replace('_', ' ').capitalize()
            
            if not Document.objects.filter(file=full_path).exists():
                Document.objects.create(
                    title=title,
                    file=full_path,
                    category=category,
                    establishment='RED',
                    author=author,
                    description='Documento importado automáticamente de la base de conocimientos.',
                    version='1.0'
                )
                self.stdout.write(f"Registrado: {title}")
                count += 1
            else:
                self.stdout.write(f"Saltando (ya existe): {filename}")

        self.stdout.write(self.style.SUCCESS(f"Sincronización completada. {count} nuevos documentos registrados."))
