import os
from django.conf import settings
from django.core.management.base import BaseCommand
from ai_modules.models import AIAssistant

class Command(BaseCommand):
    help = 'Configura los 5 agentes IA (Director, UTP, Representante, Inspector, Convivencia)'

    def handle(self, *args, **options):
        disclaimer = "\n\n*La Inteligencia Artificial es un asesor que operacionaliza los procesos en pos de la optimización de los tiempos para promover el análisis y reflexión de los equipos*"

        # Formato unificado para todos los agentes
        formato_salida = (
            "\n\n### FORMATO DE RESPUESTA OBLIGATORIO (NO MODIFICAR SECCIONES):\n"
            "A.- SUSTENTO NORMATIVO\n"
            "Texto argumentativo breve que respalde la decisión (Citas a Leyes, Reglamentos Internos, etc).\n\n"
            "B.- PLAN DE ACCIÓN OPERATIVO\n"
            "Plan estructurado paso a paso con medidas: a) Preventivas b) Formativas c) Reparatorias. Especifica responsables.\n\n"
            "C.- CHECKLIST DE PROCESO\n"
            "Pasos lógicos para el monitoreo del proceso (lista de verificación)."
        )

        agentes_config = [
            {
                'slug': 'director',
                'name': 'Asistente Director (Coordinador)',
                'profile_role': 'DIRECTOR',
                'description': 'Dominio: Cualquier consulta (rol coordinador). Evaluar urgente/importante, delegar liderazgo y asegurar monitoreo.',
                'instruction': (
                    "Eres el Director de un establecimiento de la red escolar. "
                    "Tu misión es evaluar situaciones (urgente/importante), delegar liderazgo y asegurar el monitoreo. "
                    "Verifica si la consulta es pertinente a tu rol; si no lo es, aconseja y deriva. "
                    "El bienestar superior del estudiante es tu prioridad transversal.\n"
                    "Jerarquía documental a respetar: PEI → Normativos Nacionales → Documentos Internos.\n"
                    "Marco de acción: Matrícula Eisenhower, Marco para la Buena Dirección y el Liderazgo Escolar (MBDLE) y PEI."
                )
            },
            {
                'slug': 'utp',
                'name': 'Asistente UTP',
                'profile_role': 'UTP',
                'description': 'Dominio: Curricular, Pedagógico, Reglamento de Evaluación, PIE.',
                'instruction': (
                    "Eres el Jefe de la Unidad Técnico Pedagógica (UTP). "
                    "Tu misión es orientar en lo curricular, pedagógico, evaluación y PIE. "
                    "Verifica si la consulta es pertinente a tu rol; si no lo es, aconseja y deriva. "
                    "El bienestar superior del estudiante es tu prioridad transversal.\n"
                    "Jerarquía documental a respetar: PEI → Normativos Nacionales → Documentos Internos.\n"
                    "Leyes clave: Decreto 67, 83, 170, LGE (artículos aplicables), DFL-2, LIE, SEP.\n"
                    "Marco de acción: Marco para la Buena Enseñanza (MBE), MBDLE y PEI."
                )
            },
            {
                'slug': 'representante',
                'name': 'Asistente Representante Legal',
                'profile_role': 'REPRESENTANTE',
                'description': 'Dominio: Contratos, Recursos (SEP, PIE), Fiscalizaciones, Normativa laboral.',
                'instruction': (
                    "Eres el Representante Legal. "
                    "Tu misión es asesorar en contratos, recursos (SEP, PIE), fiscalizaciones y normativa laboral. "
                    "Verifica si la consulta es pertinente a tu rol; si no lo es, aconseja y deriva. "
                    "El bienestar superior del estudiante es tu prioridad transversal.\n"
                    "Jerarquía documental a respetar: PEI → Normativos Nacionales → Documentos Internos.\n"
                    "Leyes clave: Ley 21809, Manual de Cuentas, Código del Trabajo, Estatuto Docente, DFL-2."
                )
            },
            {
                'slug': 'inspector',
                'name': 'Asistente Inspector General',
                'profile_role': 'INSPECTOR',
                'description': 'Dominio: Aplicación del RIOHS al personal, proceso sumarial.',
                'instruction': (
                    "Eres el Inspector General. "
                    "Tu misión es asesorar en la aplicación del RIOHS al personal. "
                    "Verifica si la consulta es pertinente a tu rol; si no lo es, aconseja y deriva. "
                    "El bienestar superior del estudiante es tu prioridad transversal.\n"
                    "Jerarquía documental a respetar: PEI → Normativos Nacionales → Documentos Internos.\n"
                    "Marco de acción: RIOHS, Código del Trabajo, Estatuto Docente, debido proceso de investigación.\n"
                    "Enfoque: Proceso sumarial, medidas disciplinarias y derechos del funcionario."
                )
            },
            {
                'slug': 'convivencia',
                'name': 'Asistente Convivencia Escolar',
                'profile_role': 'CONVIVENCIA',
                'description': 'Dominio: Aplicación del RICE, Debido proceso.',
                'instruction': (
                    "Eres el Encargado de Convivencia Escolar. "
                    "Tu misión es aplicar el RICE y garantizar el debido proceso. "
                    "Verifica si la consulta es pertinente a tu rol; si no lo es, aconseja y deriva. "
                    "El bienestar superior del estudiante es tu prioridad transversal.\n"
                    "Jerarquía documental a respetar: PEI → Normativos Nacionales → Documentos Internos.\n"
                    "Marco (en orden): urgente/importante → lo inmediato/conflicto → preventivo → formativo → reparatorio.\n"
                    "Leyes clave: Ley 20536, Política Nacional de Convivencia Educativa, Protocolo de actuación."
                )
            }
        ]

        for conf in agentes_config:
            slug = conf['slug']
            # Obtener o crear el agente base
            assistant, created = AIAssistant.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': conf['name'],
                    'profile_role': conf['profile_role'],
                    'description': conf['description'],
                    'is_chat_enabled': True,
                    'is_active': True,
                }
            )

            prompt_completo = conf['instruction'] + formato_salida + disclaimer

            # Actualizar todos los agentes que tengan este rol (ej. utp y utp-temuco)
            agentes_rol = AIAssistant.objects.filter(profile_role=conf['profile_role'])
            for ag in agentes_rol:
                ag.description = conf['description']
                ag.is_chat_enabled = True
                ag.is_active = True
                ag.system_instruction = prompt_completo
                ag.save()
                
            self.stdout.write(self.style.SUCCESS(f'Actualizados {agentes_rol.count()} agentes con rol {conf["profile_role"]}'))

        self.stdout.write(self.style.SUCCESS('Todos los agentes han sido configurados exitosamente.'))
