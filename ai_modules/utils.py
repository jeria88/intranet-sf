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

def get_relevant_chunks(assistant, query, top_n=8):
    """
    Busca los fragmentos más relevantes en la BD usando consultas SQL
    y expande el contexto con fragmentos vecinos.
    """
    from .models import AIKnowledgeChunk
    from django.db.models import Q
    
    chunks_qs = AIKnowledgeChunk.objects.filter(assistant=assistant)
    
    if not chunks_qs.exists():
        return ""
    
    # Extraer palabras clave significativas (>3 chars, sin stopwords)
    stopwords = {
        'esto', 'pero', 'como', 'para', 'esta', 'estos', 'este',
        'una', 'unas', 'unos', 'caso', 'sobre', 'estudiante', 'tiene',
        'todas', 'siempre', 'también', 'cuando', 'desde', 'fueron',
        'está', 'están', 'donde', 'porque', 'entre', 'hasta', 'puede',
        'clase', 'clases', 'trabajo', 'docente',
    }
    keywords = [w.lower() for w in query.split() if len(w) > 3 and w.lower() not in stopwords]
    
    if not keywords:
        return "\n\n---\n\n".join([c.content for c in chunks_qs[:5]])

    # Buscar con SQL: filtro OR por cada palabra clave usando icontains
    q_filter = Q()
    # Términos normativos siempre relevantes para casos educativos
    legal_terms = [
        'evaluación', 'calificación', 'nota', 'reglamento', 'artículo',
        'rice', 'pei', 'decreto', 'formativa', 'superintendencia',
        'apoderado', 'familia', 'medida', 'procedimiento', 'plazo',
        'justificación', 'inasistencia', 'incumplimiento',
    ]
    all_search_terms = list(set(keywords + legal_terms))
    
    for term in all_search_terms:
        q_filter |= Q(content__icontains=term)
    
    matching_chunks = chunks_qs.filter(q_filter).values_list(
        'id', 'chunk_id', 'content', 'document_name', 'index', flat=False
    )

    # Puntuar resultados
    scored = []
    for pk, chunk_id, content, doc_name, idx in matching_chunks:
        score = 0
        content_lower = content.lower()
        for kw in keywords:
            if kw in content_lower:
                score += 2
        for lt in legal_terms:
            if lt in content_lower:
                score += 1
        scored.append({
            'score': score,
            'pk': pk,
            'chunk_id': chunk_id,
            'content': content,
            'document_name': doc_name or '',
            'index': idx or 0,
        })
    
    ranked = sorted(scored, key=lambda x: x['score'], reverse=True)[:top_n]
    if not ranked:
        return "\n\n---\n\n".join([c.content for c in chunks_qs[:4]])

    # Expansión por vecindad: buscar fragmentos adyacentes
    neighbor_filter = Q()
    for item in ranked:
        doc = item['document_name']
        idx = item['index']
        neighbor_filter |= Q(
            assistant=assistant,
            document_name=doc,
            index__in=[idx - 1, idx, idx + 1]
        )
    
    if neighbor_filter:
        neighbor_chunks = AIKnowledgeChunk.objects.filter(
            neighbor_filter, assistant=assistant
        ).order_by('document_name', 'index').distinct()
    else:
        neighbor_chunks = []

    seen = set()
    final = []
    for c in neighbor_chunks:
        if c.chunk_id not in seen:
            seen.add(c.chunk_id)
            final.append(c)

    return "\n\n---\n\n".join(
        [f"[Fuente: {c.document_name}]\n{c.content}" for c in final]
    )
