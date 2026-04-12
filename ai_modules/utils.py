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

def get_relevant_chunks(assistant, query, top_n=10):
    """
    Busca los fragmentos más relevantes en la base de datos para un asistente específico
    utilizando una búsqueda por palabras clave simplificada.
    """
    from .models import AIKnowledgeChunk
    
    # Obtener todos los chunks asociados al asistente
    chunks_queryset = AIKnowledgeChunk.objects.filter(assistant=assistant)
    
    if not chunks_queryset.exists():
        return ""
    
    # Limpieza básica de la consulta y obtención de palabras clave
    keywords = [w.lower() for w in query.split() if len(w) > 3]
    
    if not keywords:
        # Si no hay palabras clave largas, devolvemos los primeros 5 chunks por defecto
        default_chunks = chunks_queryset.all()[:5]
        return "\n\n---\n\n".join([c.content for c in default_chunks])

    # Puntuar fragmentos en memoria (Buscador RAG ligero)
    chunk_scores = []
    for chunk in chunks_queryset:
        score = 0
        content_lower = chunk.content.lower()
        
        # Las palabras clave en el contenido suman puntos
        for kw in keywords:
            if kw in content_lower:
                score += 1
                
        if score > 0:
            chunk_scores.append((score, chunk.content))
    
    # Ordenar por puntaje (descendente) y tomar los mejores
    ranked_chunks = sorted(chunk_scores, key=lambda x: x[0], reverse=True)
    best_chunks = [c[1] for c in ranked_chunks[:top_n]]
    
    # Si no hubo matches, devolver los primeros fragmentos para dar algo de contexto básico
    if not best_chunks:
        fallback_chunks = chunks_queryset.all()[:3]
        return "\n\n---\n\n".join([c.content for c in fallback_chunks])
        
    return "\n\n---\n\n".join(best_chunks)
