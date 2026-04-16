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
    api_key_val = getattr(settings, 'OPENAI_API_KEY', os.environ.get('OPENAI_API_KEY'))
    if not api_key_val:
        print("Falta configurar OPENAI_API_KEY en .env")
        return None
    try:
        client = openai.OpenAI(api_key=api_key_val)
        response = client.embeddings.create(
            input=[text],
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generando embedding: {e}")
        return None

def get_relevant_chunks(assistant, query, top_n=10):
    """
    Busca fragmentos relevantes usando similitud coseno con sistema de caché binario.
    Optimizado para evitar timeouts en servidores con recursos limitados (Railway Free).
    """
    from .models import AIKnowledgeChunk
    import json
    import numpy as np
    import time

    cache_dir = os.path.join(settings.BASE_DIR, 'ai_modules', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    
    matrix_path = os.path.join(cache_dir, f'vectors_{assistant.slug}.npy')
    meta_path = os.path.join(cache_dir, f'meta_{assistant.slug}.json')

    # 1. Convertir la consulta en embedding
    query_embedding = get_openai_embedding(query)
    if not query_embedding:
        return "!!! ERROR !!!\nFallo al generar embedding de consulta."

    # 2. Intentar cargar desde caché
    ids, doc_names, indices = [], [], []
    matrix = None
    cache_ready = False

    if os.path.exists(matrix_path) and os.path.exists(meta_path):
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            # Verificar si el caché es coherente con la base de datos (conteo rápido)
            db_count = AIKnowledgeChunk.objects.filter(assistant=assistant).exclude(embedding__isnull=True).count()
            if meta['count'] == db_count:
                ids = meta['ids']
                doc_names = meta['doc_names']
                indices = meta['indices']
                matrix = np.load(matrix_path)
                cache_ready = True
        except Exception as e:
            print(f"Error cargando caché: {e}")

    # 3. Si no hay caché o está desactualizado, reconstruir desde BD
    if not cache_ready:
        print(f"Reconstruyendo caché para {assistant.slug}...")
        chunk_data = AIKnowledgeChunk.objects.filter(
            assistant=assistant
        ).exclude(
            embedding__isnull=True
        ).values_list('id', 'embedding', 'document_name', 'index')

        if not chunk_data:
            return "!!! ERROR !!!\nLa base de datos no tiene fragmentos procesados."

        ids, embeddings, doc_names, indices = zip(*chunk_data)
        
        # Convertir a matriz numpy
        if isinstance(embeddings[0], str):
            matrix = np.array([json.loads(e) for e in embeddings], dtype=np.float32)
        else:
            matrix = np.array(embeddings, dtype=np.float32)
        
        # Guardar caché para la próxima vez
        np.save(matrix_path, matrix)
        with open(meta_path, 'w') as f:
            json.dump({
                'count': len(ids),
                'ids': list(ids),
                'doc_names': list(doc_names),
                'indices': list(indices)
            }, f)

    # 4. Cálculo de Similitud
    q_vec = np.array(query_embedding, dtype=np.float32)
    similarities = np.dot(matrix, q_vec)

    # 5. Boosting Normativo
    priority_patterns = ["2.-Ley-21809", "Manual-de-cuentas"]
    account_keywords = ["codigo", "cuenta", "item", "clase", "sep", "pie", "801", "802", "803", "804"]
    
    query_lower = query.lower()
    is_account_query = any(k in query_lower for k in account_keywords)
    
    priority_mask = np.zeros(len(doc_names), dtype=bool)
    for pattern in priority_patterns:
        priority_mask |= np.array([pattern in str(d) for d in doc_names])

    similarities[priority_mask] *= 10.0
    if is_account_query:
        similarities[priority_mask] *= 5.0

    # 6. Selección de Top N
    top_indices = np.argsort(similarities)[::-1][:top_n]
    
    scored_results = []
    for idx in top_indices:
        if similarities[idx] > 0.05: # Threshold reducido para mayor flexibilidad
            scored_results.append({
                'id': ids[idx],
                'doc': doc_names[idx],
                'index': indices[idx]
            })

    if not scored_results:
        return "No se encontraron fragmentos relevantes para tu consulta."

    # 7. Expansión y Contenido (Optimización: Una sola consulta)
    # Recolectar todos los índices necesarios para minimizar hits a la BD
    needed_indices = []
    for item in scored_results:
        needed_indices.extend([item['index']-1, item['index'], item['index']+1])
    
    # Traer todos los fragmentos vecinos de una vez
    relevant_docs = set(item['doc'] for item in scored_results)
    neighbors = AIKnowledgeChunk.objects.filter(
        assistant=assistant,
        document_name__in=relevant_docs,
        index__in=needed_indices
    ).order_by('document_name', 'index')

    final_chunks = list(neighbors)
    final_chunks.sort(key=lambda c: (c.document_name or '', c.index or 0))

    return "\n\n---\n\n".join(
        [f"[Fuente: {c.document_name} - Sec: {c.index}]\n{c.content}" for c in final_chunks]
    )
