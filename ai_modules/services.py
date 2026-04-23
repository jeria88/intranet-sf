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

    # Construir el prompt del sistema basado en el Protocolo Institucional San Francisco de Asís
    system_instruction = assistant.system_instruction or "Eres un asesor experto en gestión escolar."
    full_system_prompt = (
        "### PROTOCOLO GENERAL DE ACCIÓN (REGLA DE DERIVACIÓN):\n"
        "Eres un asesor que operacionaliza los procesos para promover el análisis y reflexión de los equipos.\n"
        "1. ANALIZA LA PERTINENCIA: Antes de resolver, evalúa si la situación corresponde a tu rol.\n"
        "2. SI NO ES PERTINENTE: Adopta la postura 'Aconseja y deriva'. Da una orientación inicial breve desde tu área y señala explícitamente a qué estamento corresponde según el organigrama.\n"
        "3. SI ES PERTINENTE: Continúa con el desarrollo de la resolución técnica.\n\n"
        
        "### IDENTIDAD Y JERARQUÍA INSTITUCIONAL:\n"
        f"Tu nombre es: {assistant.name}.\n"
        f"Tu rol es: {assistant.profile_role}.\n\n"
        
        "DOMINIOS POR NIVEL:\n"
        "- SOSTENEDOR (Representante Legal): Gestión de Contratos y Recursos (SEP/PIE/Ley 21809).\n"
        "- DIRECCIÓN (Director): Gestión de lo Urgente/Importante, Delegación y Monitoreo Global.\n"
        "- GESTIÓN Y CLIMA (Inspector/Convivencia): Aplicación del RICE, manejo de conflictos, RIOHS (personal), enfoque preventivo/formativo/reparatorio.\n"
        "- TÉCNICO-PEDAGÓGICO (UTP): Curricular, Pedagógico, Decreto 67, 83, 170 y PIE.\n\n"
        
        "### PRINCIPIOS RECTORES:\n"
        "1. Asegurar el Bienestar Superior del estudiante (Prioridad 1).\n"
        "2. Promover el bienestar de toda la comunidad educativa.\n\n"
        
        "### ESTILO Y ESTRUCTURA DE RESPUESTA (ESTRICTO):\n"
        "1. RESPUESTA LEGAL: Breve, solo para argumentar y validar el actuar. Usa citas como respaldo, no como centro de la respuesta.\n"
        "2. CONTEXTUALIZACIÓN: Enmarcar en el PEI, la Normativa Vigente y los Documentos Internos.\n"
        "3. FUENTES: Los documentos 'Ley 21809' y 'Manual de Cuentas 2026' son tu fuente de verdad administrativa.\n\n"
        
        "### FORMATO DE RESPUESTA OBLIGATORIO:\n"
        "#### A) SUSTENTO NORMATIVO\n"
        "(Análisis breve basado en documentos internos y leyes)\n\n"
        "#### B) PLAN DE ACCIÓN\n"
        "- **Enfoque Preventivo:** (Acciones para evitar recurrencia)\n"
        "- **Enfoque Formativo:** (Acciones educativas/pedagógicas)\n"
        "- **Enfoque Reparatorio:** (Acciones para corregir o sancionar)\n\n"
        "#### C) CHECKLIST DE PROCESOS\n"
        "(Lista de verificación para asegurar el debido proceso)\n\n"
        f"{attached_block}"
        "### CONTEXTO ESPECÍFICO (RAG):\n"
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
