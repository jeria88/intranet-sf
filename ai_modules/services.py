import requests
from django.conf import settings
from .utils import get_relevant_chunks

def call_deepseek_ai(assistant, messages_history, user_query):
    """
    Realiza una llamada a la API de DeepSeek inyectando el contexto RAG
    y el historial de la conversación.
    """
    api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
    base_url = getattr(settings, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    
    if not api_key:
        return "Error: DEEPSEEK_API_KEY no configurado."

    # RAG: Recuperar fragmentos relevantes de la BD
    relevant_context = get_relevant_chunks(assistant, user_query)

    # Construir el prompt del sistema con identidad + contexto + formato de 6 puntos
    system_instruction = assistant.system_instruction or "Eres un asistente servicial."
    full_system_prompt = (
        f"{system_instruction}\n\n"
        "### INSTRUCCIONES CRÍTICAS:\n"
        "1. El 'CONTEXTO DE DOCUMENTOS' contiene fragmentos de los reglamentos REALES del colegio.\n"
        "2. Utiliza estos fragmentos como base legal para fundamentar tu análisis.\n"
        "3. Cita el artículo, sección o documento específico cuando fundamentes cada punto.\n"
        "4. Si un punto no tiene sustento directo en el contexto, indica qué normativa general aplicaría.\n"
        "5. Nunca menciones que eres DeepSeek ni que eres un modelo de IA.\n"
        "6. Mantén siempre tu identidad como asistente UTP de la Escuela San Francisco de Asís.\n\n"
        "### CONTEXTO DE DOCUMENTOS RELEVANTES (Fuente de Verdad):\n"
        f"{relevant_context}\n"
        "--- FIN DEL CONTEXTO ---"
    )
    
    messages = [{"role": "system", "content": full_system_prompt}]
    
    for msg in messages_history:
        messages.append({"role": msg['role'], "content": msg['content']})
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "stream": False
    }
    
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=90
        )
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling DeepSeek: {e}")
        return f"Lo siento, hubo un error al procesar tu consulta con la IA. ({str(e)})"
