import os
from pypdf import PdfReader
from django.conf import settings

def extract_text_from_pdf(file_path):
    """Extrae el texto de un archivo PDF usando pypdf."""
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
    except Exception as e:
        print(f"Error extrayendo texto de PDF: {e}")
    return text

def process_knowledge_base_file(knowledge_base_obj):
    """Procesa un objeto AIKnowledgeBase, extrae su texto y actualiza el asistente."""
    if not knowledge_base_obj.file:
        return
    
    file_path = knowledge_base_obj.file.path
    extracted_text = extract_text_from_pdf(file_path)
    
    knowledge_base_obj.extracted_text = extracted_text
    knowledge_base_obj.is_processed = True
    knowledge_base_obj.save(update_fields=['extracted_text', 'is_processed'])
    
    # Actualizar el contexto del asistente asociado
    knowledge_base_obj.assistant.update_context_text()

def get_relevant_chunks(full_text, query, chunk_size=1500, top_n=10):
    """
    Divide el texto en fragmentos y retorna los N más relevantes basado en 
    coincidencia de palabras clave (Buscador RAG ligero).
    """
    if not full_text:
        return ""
    
    # Limpieza básica de la consulta
    keywords = [w.lower() for w in query.split() if len(w) > 3]
    if not keywords:
        # Si no hay palabras clave largas, devolvemos el inicio del texto
        return full_text[:chunk_size * top_n]

    # Dividir el texto en fragmentos con solapamiento
    chunks = []
    for i in range(0, len(full_text), chunk_size - 200):
        chunks.append(full_text[i:i + chunk_size])
    
    # Puntuar fragmentos
    chunk_scores = []
    for chunk in chunks:
        score = 0
        chunk_lower = chunk.lower()
        for kw in keywords:
            if kw in chunk_lower:
                score += 1
        chunk_scores.append((score, chunk))
    
    # Ordenar por puntaje (descendente) y tomar los mejores
    ranked_chunks = sorted(chunk_scores, key=lambda x: x[0], reverse=True)
    best_chunks = [c[1] for c in ranked_chunks[:top_n] if c[0] > 0]
    
    # Si no hubo matches, devolver los primeros fragmentos por precaución
    if not best_chunks:
        return full_text[:chunk_size * top_n]
        
    return "\n\n---\n\n".join(best_chunks)
