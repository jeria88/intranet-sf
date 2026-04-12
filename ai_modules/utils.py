import os
from pypdf import PdfReader
from django.conf import settings
import math

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
    
    knowledge_base_obj.assistant.update_context_text()


# ── Motor de Embeddings API (Cero consumo RAM) ──────────────────────────

def cosine_similarity(v1, v2):
    """Calcula similitud coseno en Python puro."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

def get_openai_embedding(text):
    import openai
    openai.api_key = getattr(settings, 'OPENAI_API_KEY', os.environ.get('OPENAI_API_KEY'))
    if not openai.api_key:
        print("Falta configurar OPENAI_API_KEY en .env")
        return None
    try:
        response = openai.embeddings.create(
            input=[text],
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generando embedding: {e}")
        return None

def get_relevant_chunks(assistant, query, top_n=10):
    """
    Busca fragmentos relevantes usando similitud coseno en embeddings pre-calculados.
    Evita la carga de modelos en RAM, usando puramente la base de datos y Python.
    """
    from .models import AIKnowledgeChunk

    # 1. Convertir la consulta en embedding
    query_embedding = get_openai_embedding(query)
    
    chunks = AIKnowledgeChunk.objects.filter(assistant=assistant).exclude(embedding__isnull=True)
    if not chunks.exists() or not query_embedding:
        # Fallback si no hay embeddings cargados: retornar los primeros
        qs = AIKnowledgeChunk.objects.filter(assistant=assistant)
        return "\n\n---\n\n".join([f"[Fuente: {c.document_name}]\n{c.content}" for c in qs[:5]])

    # 2. Calcular similitud coseno en memoria de Python (~1200 items es casi instantáneo)
    scored_chunks = []
    for chunk in chunks:
        if not chunk.embedding: continue
        sim = cosine_similarity(query_embedding, chunk.embedding)
        if sim > 0.1: # Threshold básico
            scored_chunks.append({
                'score': sim,
                'chunk': chunk
            })

    # 3. Ordenar por score
    scored_chunks.sort(key=lambda x: x['score'], reverse=True)
    top_items = scored_chunks[:top_n]
    
    if not top_items:
        return "\n\n---\n\n".join([c.content for c in chunks[:5]])

    # 4. Expansión por vecindad
    expanded_ids = set()
    final_chunks = []

    for item in top_items:
        c = item['chunk']
        doc = c.document_name
        idx = c.index

        neighbors = AIKnowledgeChunk.objects.filter(
            assistant=assistant,
            document_name=doc,
            index__in=[idx - 1, idx, idx + 1]
        ).order_by('index')

        for n in neighbors:
            if n.chunk_id not in expanded_ids:
                expanded_ids.add(n.chunk_id)
                final_chunks.append(n)

    # Ordenar por documento e índice
    final_chunks.sort(key=lambda c: (c.document_name or '', c.index or 0))

    return "\n\n---\n\n".join(
        [f"[Fuente: {c.document_name} - Sec: {c.index}]\n{c.content}" for c in final_chunks]
    )
