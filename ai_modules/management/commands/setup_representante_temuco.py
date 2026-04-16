import json
import os
import uuid
from django.core.management.base import BaseCommand
from ai_modules.models import AIAssistant, AIKnowledgeChunk
from ai_modules.utils import get_openai_embedding

class Command(BaseCommand):
    help = 'Carga la base de conocimientos para Representante Temuco desde un JSON'

    def handle(self, *args, **options):
        json_path = '/home/nikka/Intranet/intranet_railway/ai_modules/knowledge_base/representante_temuco.json'
        
        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'No se encontró el archivo {json_path}'))
            return

        # 1. Crear o actualizar el asistente
        # Aseguramos que tenga el mismo perfil que UTP Temuco para habilitar el chat
        assistant, created = AIAssistant.objects.update_or_create(
            slug='representante.temuco',
            defaults={
                'name': 'Asistente Representante Legal (Temuco)',
                'profile_role': 'REPRESENTANTE',
                'establishment': 'TEMUCO',
                'is_active': True,
                'system_instruction': (
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
            }
        )

        self.stdout.write(self.style.SUCCESS(f'Asistente {assistant.slug} configurado correctamente con rol REPRESENTANTE y EST: TEMUCO'))

        # 2. Cargar chunks del JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            chunks = data.get('chunks', [])

        total = len(chunks)
        self.stdout.write(self.style.NOTICE(f'Procesando {total} fragmentos de conocimiento...'))
        
        # Opcional: Limpiar chunks previos para evitar duplicados en re-ejecución
        AIKnowledgeChunk.objects.filter(assistant=assistant).delete()

        count = 0
        limit = 300 # Límite para prueba inicial (puedes subirlo si deseas)
        for index, item in enumerate(chunks[:limit]): 
            text = item.get('text_content', '')
            if not text: continue
                
            embedding = get_openai_embedding(text)
            metadata = item.get('legal_metadata', {})
            source_file = metadata.get('source_file', 'representante_temuco.json')
            
            AIKnowledgeChunk.objects.create(
                assistant=assistant,
                content=text,
                embedding=json.dumps(embedding) if embedding else None,
                metadata=json.dumps(metadata),
                chunk_id=f"rep_tem_{uuid.uuid4().hex[:8]}_{index}",
                document_name=source_file,
                index=index
            )
            count += 1
            if count % 50 == 0:
                self.stdout.write(f'Procesados {count}/{limit}...')

        self.stdout.write(self.style.SUCCESS(f'Motor de conocimiento activado: {count} fragmentos cargados.'))

