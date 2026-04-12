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


# ── Motor de Embeddings TF-IDF ──────────────────────────────────────────
# Cache en memoria: se construye una vez por worker de Gunicorn
_tfidf_cache = {}

def _build_tfidf_index(assistant):
    """
    Construye un índice TF-IDF para todos los chunks de un asistente.
    Se cachea en memoria del worker para consultas subsiguientes.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    from .models import AIKnowledgeChunk

    chunks = list(
        AIKnowledgeChunk.objects.filter(assistant=assistant)
        .order_by('document_name', 'index')
    )

    if not chunks:
        return None

    texts = [c.content for c in chunks]

    # Stopwords en español para que el vectorizador ignore ruido
    spanish_stops = [
        'de', 'la', 'que', 'el', 'en', 'los', 'del', 'las', 'por',
        'con', 'una', 'para', 'son', 'como', 'más', 'pero', 'sus',
        'le', 'ya', 'este', 'esta', 'estos', 'estas', 'ese', 'esa',
        'ser', 'al', 'un', 'se', 'lo', 'no', 'si', 'su', 'hay',
        'también', 'fue', 'han', 'está', 'muy', 'tiene', 'puede',
        'donde', 'sobre', 'todo', 'entre', 'cuando', 'cada', 'desde',
        'sin', 'hasta', 'otro', 'otra', 'otros', 'otras',
    ]

    vectorizer = TfidfVectorizer(
        max_features=8000,
        stop_words=spanish_stops,
        ngram_range=(1, 2),   # Captura bigramas como "reglamento evaluación"
        sublinear_tf=True,     # Suaviza frecuencias altas
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    index = {
        'vectorizer': vectorizer,
        'matrix': tfidf_matrix,
        'chunks': chunks,
    }
    _tfidf_cache[assistant.pk] = index
    print(f"TF-IDF index built: {len(chunks)} chunks, {tfidf_matrix.shape[1]} features")
    return index


def _get_tfidf_index(assistant):
    """Obtiene el índice desde cache o lo construye."""
    if assistant.pk in _tfidf_cache:
        return _tfidf_cache[assistant.pk]
    return _build_tfidf_index(assistant)


def get_relevant_chunks(assistant, query, top_n=10):
    """
    Busca fragmentos relevantes usando similitud coseno sobre embeddings TF-IDF.
    Mucho más rápido y preciso que búsqueda por keywords.
    """
    from sklearn.metrics.pairwise import cosine_similarity
    from .models import AIKnowledgeChunk

    index = _get_tfidf_index(assistant)
    if not index:
        return ""

    # Vectorizar la consulta del usuario
    query_vec = index['vectorizer'].transform([query])

    # Calcular similitud coseno contra todos los chunks (~50ms para 1200 chunks)
    similarities = cosine_similarity(query_vec, index['matrix']).flatten()

    # Obtener los top_n índices más similares
    top_indices = similarities.argsort()[-top_n:][::-1]
    top_chunks = [index['chunks'][i] for i in top_indices if similarities[i] > 0.01]

    if not top_chunks:
        # Fallback: devolver primeros chunks
        return "\n\n---\n\n".join([c.content for c in index['chunks'][:5]])

    # Expansión por vecindad: traer el chunk anterior y posterior
    expanded_ids = set()
    final_chunks = []

    for chunk in top_chunks:
        doc = chunk.document_name
        idx = chunk.index

        neighbors = AIKnowledgeChunk.objects.filter(
            assistant=assistant,
            document_name=doc,
            index__in=[idx - 1, idx, idx + 1]
        ).order_by('index')

        for n in neighbors:
            if n.chunk_id not in expanded_ids:
                expanded_ids.add(n.chunk_id)
                final_chunks.append(n)

    # Ordenar por documento e índice para mantener coherencia narrativa
    final_chunks.sort(key=lambda c: (c.document_name or '', c.index or 0))

    return "\n\n---\n\n".join(
        [f"[Fuente: {c.document_name}]\n{c.content}" for c in final_chunks]
    )
