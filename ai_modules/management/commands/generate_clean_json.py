import json
import os
import re
from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Genera utp_temuco.json limpio desde utp_temuco_model.md'

    def handle(self, *args, **options):
        md_path = os.path.join(settings.BASE_DIR, 'ai_modules', 'knowledge_base', 'utp_temuco_model.md')
        json_output_path = os.path.join(settings.BASE_DIR, 'ai_modules', 'knowledge_base', 'utp_temuco.json')

        if not os.path.exists(md_path):
            self.stdout.write(self.style.ERROR(f'Archivo MD no encontrado: {md_path}'))
            return

        with open(md_path, 'r', encoding='utf-8') as f:
            full_text = f.read()

        # Limpieza básica: quitar líneas de instrucciones de inicio si existen
        # (Las primeras líneas son "lee el siguiente reglamento...")
        lines = full_text.splitlines()
        clean_lines = [l for l in lines if not l.strip().startswith('lee el siguiente') and not l.strip().startswith('ahora lee los documentos')]
        text = "\n".join(clean_lines)

        # Chunker simple: Dividir por secciones (headers) o por tamaño con solapamiento
        # Para asegurar que las citas se mantengan, intentaremos dividir por Artículos si es posible,
        # o simplemente por bloques razonables de 1500 caracteres con 300 de solapamiento.
        
        chunks = []
        chunk_size = 1500
        overlap = 300
        
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            
            # Crear el objeto con el formato esperado por setup_utp_temuco.py
            chunk_data = {
                "texto_contenido": chunk_text,
                "metadatos": {
                    "id_establecimiento": "temuco",
                    "rol_objetivo": "utp",
                    "tipo_documento": "Documento Unificado (RE+PEI+RICE)",
                    "fuente_archivo": "utp_temuco_model.md",
                    "chunk_id": f"clean_{start}"
                }
            }
            chunks.append(chunk_data)
            start += (chunk_size - overlap)

        with open(json_output_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=4)

        self.stdout.write(self.style.SUCCESS(f'Regenerado {json_output_path} con {len(chunks)} fragmentos limpios.'))
