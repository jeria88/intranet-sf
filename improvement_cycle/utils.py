import requests
import json
import os
from .models import ImprovementGoal, ImprovementAction
from django.conf import settings

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

def generate_cycle_content_ai(goal):
    """
    Usa DeepSeek para transformar los objetivos estratégicos en una ruta de procesos e indicadores.
    """
    if not goal.strategic_objectives or not DEEPSEEK_API_KEY:
        return False

    objectives_text = "\n".join(goal.strategic_objectives) if isinstance(goal.strategic_objectives, list) else goal.strategic_objectives
    
    import time
    import random
    seed = f"{int(time.time())}-{random.randint(1000, 9999)}"

    prompt = f"""
    Como experto en gestión escolar y mejora continua, analiza los siguientes OBJETIVOS ESTRATÉGICOS y genera un plan de acción dividido en el CICLO DE MEJORA (4 etapas).
    
    SEED DE VARIABILIDAD: {seed}

    ESTRUCTURA DEL CICLO:
    Etapa 1: Análisis (Diagnóstico inicial)
    Etapa 2: Planificación (Diseño de la estrategia)
    Etapa 3: Implementación (Ejecución de las tareas clave)
    Etapa 4: Checklist de Acciones (Hitos concretos que miden el avance)

    OBJETIVOS ESTRATÉGICOS:
    {objectives_text}
    
    Debes responder ÚNICAMENTE con un objeto JSON con la siguiente estructura:
    {{
        "etapas": [
            {{"etapa": "Análisis", "descripcion": "..."}},
            {{"etapa": "Planificación", "descripcion": "..."}},
            {{"etapa": "Implementación", "descripcion": "..."}},
            {{"etapa": "Checklist de Acciones", "descripcion": "Hitos de cumplimiento para medir el progreso"}}
        ],
        "acciones": [
            {{"titulo": "Hito 1", "descripcion": "...", "peso": 20}},
            {{"titulo": "Hito 2", "descripcion": "...", "peso": 20}},
            ...
        ],
        "indicadores": [
            {{"name": "...", "target": "..."}}
        ]
    }}
    
    Genera 5 a 8 acciones concretas en el array "acciones". La suma de los pesos de las acciones debe ser 100.
    """

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Eres un consultor experto en mejora educativa. Responde solo en JSON."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.8
    }

    try:
        response = requests.post(f"{DEEPSEEK_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=45)
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content']
            data = json.loads(result)
            
            if not isinstance(data, dict):
                return False

            # Guardar en el modelo
            goal.process_route = data.get('etapas', [])
            goal.indicators = data.get('indicadores', [])
            goal.save()
            
            # Crear las acciones de mejora (el verdadero checklist que mide %)
            for action_data in data.get('acciones', []):
                title = action_data.get('titulo') or action_data.get('title')
                description = action_data.get('descripcion') or action_data.get('description') or ""
                weight = action_data.get('peso') or action_data.get('weight') or 10.0
                
                ImprovementAction.objects.create(
                    goal=goal,
                    title=str(title)[:200],
                    description=str(description),
                    weight=float(weight),
                    deadline=goal.deadline
                )

            
            # Si es para una reunión, añadir las metas automáticas
            if goal.is_meeting_cycle:
                create_meeting_default_actions(goal)
                
            return True
    except Exception as e:
        print(f"Error AI Cycle: {e}")
    finally:
        goal.is_generating = False
        goal.save(update_fields=['is_generating'])
    return False


def create_meeting_default_actions(goal):
    """Añade las acciones estándar para ciclos de reuniones."""
    default_actions = [
        {"title": "Grabación de Video", "desc": "Carga automática del video de la reunión."},
        {"title": "Lista de Participantes", "desc": "Registro de asistencia detectado por Daily.co."},
        {"title": "Acta de Reunión", "desc": "Documento generado por IA con el resumen de la sesión."},
        {"title": "Acuerdos Redactados", "desc": "Lista de compromisos extraídos de la conversación."}
    ]
    
    for act in default_actions:
        # Evitar duplicados si ya existen
        if not ImprovementAction.objects.filter(goal=goal, title=act['title']).exists():
            ImprovementAction.objects.create(
                goal=goal,
                title=act['title'],
                description=act['desc'],
                weight=5.0, # Peso menor para estas tareas administrativas
                deadline=goal.deadline
            )
