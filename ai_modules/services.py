import requests
from django.conf import settings

def call_deepseek_ai(system_instruction, context_text, messages_history):
    """
    Realiza una llamada a la API de DeepSeek inyectando el contexto (RAG) 
    y el historial de la conversación.
    """
    api_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
    base_url = getattr(settings, 'DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    
    if not api_key:
        return "Error: DEEPSEEK_API_KEY no configurado."

    # Combinamos la instrucción de sistema con el contexto de los documentos
    full_system_prompt = f"{system_instruction}\n\nCONTEXTO DE DOCUMENTOS (Fuente de verdad):\n{context_text}"
    
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
