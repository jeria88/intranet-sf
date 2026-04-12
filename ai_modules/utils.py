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

def get_relevant_chunks(assistant, query, top_n=15):
    """
    Busca los fragmentos más relevantes y expande el contexto incluyendo
    fragmentos vecinos del mismo documento. (Fase 2: Inteligencia Normativa)
    """
    from .models import AIKnowledgeChunk
    from django.db.models import Q
    
    # 1. Obtener todos los chunks asociados al asistente
    chunks_queryset = AIKnowledgeChunk.objects.filter(assistant=assistant)
    
    if not chunks_queryset.exists():
        return ""
    
    # 2. Obtener palabras clave pesadas (ignorar ruido)
    stopwords = {'esto', 'pero', 'como', 'para', 'esta', 'estos', 'este', 'una', 'unas', 'unos', 'caso', 'sobre', 'estudiante'}
    keywords = [w.lower() for w in query.split() if len(w) > 3 and w.lower() not in stopwords]
    
    if not keywords:
        default_chunks = chunks_queryset.all()[:5]
        return "\n\n---\n\n".join([c.content for c in default_chunks])

    # 3. Puntuar fragmentos
    scored_chunks = []
    for chunk in chunks_queryset:
        score = 0
        content_lower = chunk.content.lower()
        for kw in keywords:
            if kw in content_lower:
                score += 1
                # Boost para términos específicos de reglamentos
                if kw in ['reglamento', 'artículo', 'evaluación', 'nota', 'rice', 'pei']:
                    score += 2
        
        if score > 0:
            scored_chunks.append({
                'score': score,
                'chunk': chunk
            })
    
    # 4. Ordenar y tomar los mejores N
    ranked = sorted(scored_chunks, key=lambda x: x['score'], reverse=True)[:top_n]
    if not ranked:
        return "\n\n---\n\n".join([c.content for c in chunks_queryset.all()[:4]])

    # 5. Expansión por vecindad: Para cada chunk top, buscar su anterior y posterior
    expanded_chunk_ids = set()
    final_chunks = []
    
    for item in ranked:
        c = item['chunk']
        doc = c.document_name
        idx = c.index
        
        # Buscar vecinos en la BD
        neighbors = AIKnowledgeChunk.objects.filter(
            assistant=assistant,
            document_name=doc,
            index__in=[idx - 1, idx, idx + 1]
        ).order_by('index')
        
        for n in neighbors:
            if n.chunk_id not in expanded_chunk_ids:
                expanded_chunk_ids.add(n.chunk_id)
                final_chunks.append(n)

    # Ordenar los fragmentos finales por documento e índice para coherencia
    final_chunks = sorted(final_chunks, key=lambda x: (x.document_name, x.index))
    
    return "\n\n---\n\n".join([f"[{c.document_name} - Art/Sec]: {c.content}" for c in final_chunks])
