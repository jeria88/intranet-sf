import os
from pypdf import PdfReader
from django.conf import settings
import math
import numpy as np
import json
import gc

# Caché en memoria para evitar recargas constantes en servidores con RAM limitada
_VECTOR_RESOURCES = {}

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

    # 2. Intentar cargar desde caché (Memoria RAM persistente en el proceso)
    cached = _VECTOR_RESOURCES.get(assistant.slug)
    db_count_trigger = AIKnowledgeChunk.objects.filter(assistant=assistant).exclude(embedding__isnull=True).count()

    if cached and cached['meta']['count'] == db_count_trigger:
        ids = cached['ids']
        doc_names = cached['doc_names']
        indices = cached['indices']
        matrix = cached['matrix']
        priority_mask = cached['priority_mask']
        cache_ready = True
    elif os.path.exists(matrix_path) and os.path.exists(meta_path):
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            if meta['count'] == db_count_trigger:
                ids = meta['ids']
                doc_names = meta['doc_names']
                indices = meta['indices']
                # mmap_mode='r' es CLAVE: Mantiene el archivo en disco y solo carga lo que se usa en el producto punto
                matrix = np.load(matrix_path, mmap_mode='r')
                
                # Pre-calcular el priority_mask una sola vez para ahorrar CPU
                p_patterns = ["2.-Ley-21809", "Manual-de-cuentas"]
                p_mask = np.zeros(len(doc_names), dtype=bool)
                for pattern in p_patterns:
                    p_mask |= np.array([pattern in str(d) for d in doc_names])
                
                # Guardar en el singleton del proceso
                _VECTOR_RESOURCES[assistant.slug] = {
                    'ids': ids,
                    'doc_names': doc_names,
                    'indices': indices,
                    'matrix': matrix,
                    'meta': meta,
                    'priority_mask': p_mask
                }
                priority_mask = p_mask
                cache_ready = True
        except Exception as e:
            print(f"Error cargando caché: {e}")
            if assistant.slug in _VECTOR_RESOURCES:
                del _VECTOR_RESOURCES[assistant.slug]

    # 3. Si no hay caché o está desactualizado, reconstruir desde BD
    if not cache_ready:
        import gc
        print(f"Reconstruyendo caché para {assistant.slug} (Iterativo para bajo RAM)...")
        
        queryset = AIKnowledgeChunk.objects.filter(
            assistant=assistant
        ).exclude(
            embedding__isnull=True
        ).only('id', 'embedding', 'document_name', 'index')

        db_count = queryset.count()
        if db_count == 0:
            return "!!! ERROR !!!\nLa base de datos no tiene fragmentos procesados."

        # Pre-asignar memoria para la matriz y listas (más eficiente que append dinámico)
        matrix = np.zeros((db_count, 1536), dtype=np.float32)
        ids = [None] * db_count
        doc_names = [None] * db_count
        indices = [None] * db_count

        # Procesar en bloques para no saturar memoria
        for i, chunk in enumerate(queryset.iterator(chunk_size=500)):
            ids[i] = chunk.id
            doc_names[i] = chunk.document_name
            indices[i] = chunk.index
            
            emb = chunk.embedding
            if isinstance(emb, str):
                emb = json.loads(emb)
            matrix[i] = emb
            
            # Limpieza periódica de referencias de Django
            if i % 1000 == 0:
                gc.collect()

        # Guardar caché para la próxima vez
        try:
            np.save(matrix_path, matrix)
            meta_payload = {
                'count': db_count,
                'ids': ids,
                'doc_names': doc_names,
                'indices': indices
            }
            with open(meta_path, 'w') as f:
                json.dump(meta_payload, f)
            
            # Recargar ahora con mmap para liberar la RAM usada en la reconstrucción
            matrix = np.load(matrix_path, mmap_mode='r')
            
            p_patterns = ["2.-Ley-21809", "Manual-de-cuentas"]
            priority_mask = np.zeros(len(doc_names), dtype=bool)
            for pattern in p_patterns:
                priority_mask |= np.array([pattern in str(d) for d in doc_names])

            _VECTOR_RESOURCES[assistant.slug] = {
                'ids': ids,
                'doc_names': doc_names,
                'indices': indices,
                'matrix': matrix,
                'meta': meta_payload,
                'priority_mask': priority_mask
            }
            gc.collect() 
        except Exception as e:
            print(f"Advertencia: No se pudo guardar caché en disco: {e}")

    # 4. Cálculo de Similitud
    q_vec = np.array(query_embedding, dtype=np.float32)
    similarities = np.dot(matrix, q_vec)

    # 5. Boosting Normativo (Optimizado con máscara pre-calculada)
    query_lower = query.lower()
    account_keywords = ["codigo", "cuenta", "item", "clase", "sep", "pie", "801", "802", "803", "804"]
    is_account_query = any(k in query_lower for k in account_keywords)
    
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
