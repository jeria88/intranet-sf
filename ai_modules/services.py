import requests
from django.conf import settings
from .utils import get_relevant_chunks

def call_deepseek_ai(assistant, messages_history, user_query):
    """
    Realiza una llamada a la API de DeepSeek inyectando el contexto (RAG) 
    y el historial de la conversación. Usando Fase 2 de Inteligencia Normativa.
    """
    api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
    base_url = getattr(settings, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    
    if not api_key:
        return "Error: DEEPSEEK_API_KEY no configurado."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 1. Fase 2: Expansión Legal de la Consulta
    legal_keywords_prompt = (
        "Actúa como un experto legal en educación chilena. Dado el siguiente caso de un usuario, "
        "devuelve una lista de 5 a 10 términos técnicos, artículos o conceptos normativos que deberían "
        "buscarse en un reglamento de evaluación o RICE para resolverlo.\n\n"
        f"CASO: {user_query}\n\n"
        "RESPONDE SOLO CON LOS TÉRMINOS SEPARADOS POR COMAS."
    )
    
    try:
        kw_response = requests.post(
            f"{base_url}/chat/completions", 
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": legal_keywords_prompt}], "stream": False},
            headers=headers, timeout=10
        )
        expanded_query = kw_response.json()['choices'][0]['message']['content']
        search_query = f"{user_query} {expanded_query}"
    except:
        search_query = user_query

    # 2. RAG: Recuperación con Vecindad usando la consulta expandida
    relevant_context = get_relevant_chunks(assistant, search_query)

    # 3. Construcción del Prompt Maestro de 6 Puntos
    system_instruction = assistant.system_instruction or "Eres un asistente servicial."
    full_system_prompt = (
        f"{system_instruction}\n\n"
        "### INSTRUCCIONES DE USO DEL CONTEXTO:\n"
        "1. El 'CONTEXTO DE DOCUMENTOS RELEVANTES' contiene fragmentos de los reglamentos reales del colegio.\n"
        "2. Úsalos como base legal para tu análisis de 6 puntos.\n"
        "3. Si un punto no tiene sustento en el contexto, indica qué falta en la normativa para resolverlo con total certeza.\n\n"
        "### CONTEXTO DE DOCUMENTOS RELEVANTES (Fuente de Verdad):\n"
        f"{relevant_context}\n"
        "--- FIN DEL CONTEXTO ---"
    )
    
    messages = [{"role": "system", "content": full_system_prompt}]
    
    # Añadimos el historial previo
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
        response = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling DeepSeek: {e}")
        return f"Lo siento, hubo un error al procesar tu consulta con la IA. ({str(e)})"
