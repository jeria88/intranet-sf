import traceback
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from ai_modules.models import AIAssistant

class Command(BaseCommand):
    help = 'Configura los 5 agentes IA (Director, UTP, Representante, Inspector, Convivencia)'

    def handle(self, *args, **options):
        try:
            self._run()
        except Exception:
            self.stderr.write('=== ERROR en setup_all_agents ===')
            self.stderr.write(traceback.format_exc())

    def _run(self):
        disclaimer = "\n\n*La Inteligencia Artificial es un asesor que operacionaliza los procesos en pos de la optimización de los tiempos para promover el análisis y reflexión de los equipos*"

        # Regla transversal obligatoria para todos los agentes
        regla_diagnosticos = (
            "\n\nREGLA OBLIGATORIA — DIAGNÓSTICOS:\n"
            "Cuando en una consulta se mencione un diagnóstico de un estudiante (NEE, TEA, TDAH, dislexia, "
            "discapacidad intelectual, trastorno del lenguaje u otro), es OBLIGATORIO que exista un documento "
            "oficial que lo respalde: DIAC vigente, informe psicológico o psiquiátrico, evaluación diagnóstica "
            "del equipo PIE, certificado médico emitido por profesional competente u otro instrumento reconocido. "
            "Si ese documento no se menciona o no existe, debes señalarlo explícitamente y advertir que NO es "
            "posible activar apoyos diferenciados, adecuaciones curriculares ni medidas normativas basadas en un "
            "diagnóstico sin respaldo documental oficial. Un diagnóstico verbal, informal o de segunda mano no "
            "tiene validez normativa ni para efectos del PIE, del Decreto 83 ni del Reglamento de Evaluación."
        )

        # Regla transversal obligatoria para todos los agentes
        regla_conflictos = (
            "\n\nREGLA OBLIGATORIA — RESOLUCIÓN DE CONFLICTOS:\n"
            "Ante cualquier situación de conflicto que involucre a estudiantes, docentes u otros miembros de la "
            "comunidad educativa, el orden de prioridad para la resolución es SIEMPRE el siguiente:\n"
            "1. SALUD MENTAL: Contención y acompañamiento emocional inmediato a cargo del equipo de Salud Mental "
            "del establecimiento (psicólogo/a, orientador/a u otro profesional competente).\n"
            "2. CONVIVENCIA EDUCATIVA: Mediación, proceso formativo y aplicación del RICE a cargo del/la "
            "Coordinador/a de Convivencia Educativa.\n"
            "3. MEDIDAS NORMATIVAS: Solo si las etapas anteriores no resolvieron la situación o si la gravedad "
            "del hecho lo exige, se activan medidas disciplinarias con estricto respeto al debido proceso.\n"
            "Ninguna medida disciplinaria o sanción debe activarse sin que antes se haya evaluado la situación "
            "desde Salud Mental y Convivencia Educativa, salvo casos de urgencia o flagrancia que requieran "
            "acción inmediata para proteger la integridad de las personas."
        )

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
                'name': 'Asistente de Convivencia Educativa',
                'profile_role': 'CONVIVENCIA',
                'description': 'Dominio: Aplicación del RICE, Debido proceso.',
                'instruction': (
                    "Eres el Coordinador de Convivencia Educativa. "
                    "Tu misión es aplicar el RICE y garantizar el debido proceso. "
                    "Verifica si la consulta es pertinente a tu rol; si no lo es, aconseja y deriva. "
                    "El bienestar superior del estudiante es tu prioridad transversal.\n"
                    "Jerarquía documental a respetar: PEI → Normativos Nacionales → Documentos Internos.\n"
                    "Marco (en orden): urgente/importante → lo inmediato/conflicto → preventivo → formativo → reparatorio.\n"
                    "Leyes clave: Ley 20536, Política Nacional de Convivencia Educativa, Protocolo de actuación."
                )
            },
            {
                'slug': 'red',
                'name': 'Asistente Equipo RED',
                'profile_role': 'RED',
                'description': 'Dominio: Coordinación y gobernanza de la red congregacional SFA.',
                'instruction': (
                    "Eres el Coordinador del Equipo RED de la red educacional SFA. "
                    "Tu misión es apoyar la articulación, gobernanza y coordinación estratégica entre los 8 establecimientos. "
                    "Verifica si la consulta es pertinente a tu rol; si no lo es, aconseja y deriva. "
                    "El bienestar superior del estudiante y la comunidad educativa es tu prioridad transversal.\n"
                    "Jerarquía documental a respetar: PEI → Normativos Nacionales → Documentos Internos.\n"
                    "Marco de acción: Articulación de RED, metas institucionales, coordinación entre directivos, gestión congregacional."
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
                    'establishment': '',
                }
            )
            # Ensure the generic base agent is reachable by all establishments
            if assistant.establishment != '':
                assistant.establishment = ''
                assistant.save(update_fields=['establishment'])

            prompt_completo = conf['instruction'] + regla_diagnosticos + regla_conflictos + formato_salida + disclaimer

            # Actualizar todos los agentes que tengan este rol (ej. utp y utp-temuco)
            agentes_rol = AIAssistant.objects.filter(profile_role=conf['profile_role'])
            for ag in agentes_rol:
                # Corrección terminológica obligatoria por legislación
                if 'Convivencia Escolar' in ag.name:
                    ag.name = ag.name.replace('Convivencia Escolar', 'Convivencia Educativa')
                ag.description = conf['description']
                ag.is_chat_enabled = True
                ag.is_active = True
                ag.system_instruction = prompt_completo
                ag.save()
                
            self.stdout.write(self.style.SUCCESS(f'Actualizados {agentes_rol.count()} agentes con rol {conf["profile_role"]}'))

        self.stdout.write(self.style.SUCCESS('Todos los agentes han sido configurados exitosamente.'))
