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

    prompt = f"""
    Como experto en gestión escolar y mejora continua, analiza los siguientes OBJETIVOS ESTRATÉGICOS y genera un plan de acción detallado.
    
    OBJETIVOS ESTRATÉGICOS:
    {goal.strategic_objectives}
    
    Debes responder ÚNICAMENTE con un objeto JSON con la siguiente estructura:
    {{
        "ruta_procesos": [
            {{"title": "Nombre de la acción", "description": "Descripción detallada", "weight": 25, "tipo": "preventivo/formativo/reparativo"}},
            ...
        ],
        "indicadores": [
            {{"name": "Nombre del indicador", "target": "Meta cuantitativa"}},
            ...
        ],
        "checklist": [
            "Ítem de verificación 1",
            "Ítem de verificación 2"
        ],
        "proyeccion_esperada": "Breve descripción de la trayectoria esperada"
    }}
    
    Genera al menos 3 acciones (una de cada tipo: preventivo, formativo, reparativo), 2 indicadores y un checklist de 4 puntos.
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
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(f"{DEEPSEEK_BASE_URL}/chat/completions", headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content']
            data = json.loads(result)
            
            # Guardar en el modelo
            goal.process_route = data.get('ruta_procesos', [])
            goal.indicators = data.get('indicadores', [])
            # Inyectar checklist en la descripción o un campo si existiera (por ahora lo guardamos en la ruta)
            if 'checklist' in data:
                goal.process_route.append({"title": "CHECKLIST DE PROCESOS", "description": "\n".join(data['checklist']), "weight": 0, "tipo": "seguimiento"})
            
            goal.save()
            
            # Crear las acciones en la base de datos
            for action_data in data.get('ruta_procesos', []):
                ImprovementAction.objects.create(
                    goal=goal,
                    title=action_data.get('title'),
                    description=action_data.get('description'),
                    weight=action_data.get('weight', 1.0),
                    deadline=goal.deadline # Usamos el plazo de la meta como base
                )
            
            # Si es para una reunión, añadir las metas automáticas
            if goal.is_meeting_cycle:
                create_meeting_default_actions(goal)
                
            return True
    except Exception as e:
        print(f"Error AI Cycle: {e}")
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
