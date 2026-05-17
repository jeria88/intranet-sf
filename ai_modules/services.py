import requests
from django.conf import settings
from .utils import get_relevant_chunks

def call_deepseek_ai(assistant, messages_history, user_query, temperature=1.0, attached_content=None):
    """
    Realiza una llamada a la API de DeepSeek inyectando el contexto RAG
    y el historial de la conversación.
    """
    api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
    base_url = getattr(settings, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    
    if not api_key:
        return "Error: DEEPSEEK_API_KEY no configurado."

    # RAG: Recuperar fragmentos relevantes de la BD
    try:
        relevant_context = get_relevant_chunks(assistant, user_query)
    except Exception as e:
        print(f"Error en RAG: {e}")
        relevant_context = "Error al recuperar contexto legal. Procede con base en conocimientos generales pero advierte al usuario."

    # Bloque de adjunto si existe
    attached_block = ""
    if attached_content:
        attached_block = (
            "\n\n### DOCUMENTO ADJUNTO POR EL USUARIO:\n"
            "El usuario ha adjuntado un documento específico para esta consulta. Analiza su contenido con ALTA PRIORIDAD para responder:\n"
            f"{attached_content}\n"
            "--- FIN DEL DOCUMENTO ADJUNTO ---\n"
        )

    # El system_instruction almacenado en BD es la fuente única de verdad del prompt.
    # services.py solo agrega las partes dinámicas: RAG y adjuntos.
    system_instruction = assistant.system_instruction or "Eres un asesor experto en normativa educacional chilena vigente."
    full_system_prompt = (
        f"{system_instruction}\n\n"
        f"{attached_block}"
        "### CONTEXTO DOCUMENTAL (RAG):\n"
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
        "temperature": temperature,
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
        return f"Lo siento, hubo un error al procesar tu consulta (DeepSeek API Error). Por favor, intenta de nuevo en unos momentos o reporta este error: {str(e)}"
