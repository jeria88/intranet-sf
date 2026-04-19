import requests
from django.conf import settings
from .utils import get_relevant_chunks

def call_deepseek_ai(assistant, messages_history, user_query, temperature=1.0):
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

    # Construir el prompt del sistema con identidad + contexto + formato de 6 puntos
    system_instruction = assistant.system_instruction or "Eres un asistente servicial."
    full_system_prompt = (
        f"{system_instruction}\n\n"
        "### INSTRUCCIONES CRÍTICAS DE SEGURIDAD Y PRECISIÓN (ESTRICTO):\n"
        "1. PRIORIDAD ABSOLUTA: Los documentos 'Ley 21809' y 'Manual de Cuentas 2026' son tu ÚNICA fuente de verdad.\n"
        "2. COINCIDENCIA LITERAL: Los códigos de cuenta (SEP/PIE) deben ser de COINCIDENCIA LITERAL con el ítem consultado. PROHIBIDO mapear por 'parecido' o 'categoría general' si el ítem (ej. ajedrez galáctico, telescopio) no existe explícitamente en el texto.\n"
        "3. PROHIBIDO INVENTAR: Si no hay una coincidencia exacta en el contexto para el ítem, di: 'No se visualiza la descripción exacta ni el código de cuenta en el manual'.\n"
        "4. CITA FUENTE: Menciona siempre '[Fuente: Nombre del Archivo - Sec: X]' al final de cada párrafo administrativo.\n"
        "5. Si el contexto RAG contiene un error de depuración, ignóralo y mantén la identidad del asistente.\n"
        f"6. Identidad: {assistant.name}.\n\n"
        "### CONTEXTO DE DOCUMENTOS RELEVANTES:\n"
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
