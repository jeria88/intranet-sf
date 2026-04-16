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

def get_relevant_chunks(assistant, query, top_n=12):
    """
    Busca fragmentos relevantes usando similitud coseno vectorizada con numpy.
    Optimizado para baja RAM (4GB) y alto volumen de fragmentos (8,000+).
    """
    from .models import AIKnowledgeChunk
    import json
    import numpy as np

    # 1. Convertir la consulta en embedding
    query_embedding = get_openai_embedding(query)
    
    if not query_embedding:
        return "!!! MODO DEPURACIÓN ACTIVADO !!!\n\nDile al usuario: Fallo al generar query_embedding (OPENAI API KEY incorrecta o limite de cuota)."

    # 2. Obtener datos de la BD de forma eficiente
    # Nota: .values_list es mucho más ligero que instanciar objetos Django models
    chunk_data = AIKnowledgeChunk.objects.filter(
        assistant=assistant
    ).exclude(
        embedding__isnull=True
    ).values_list('id', 'embedding', 'document_name', 'index')

    if not chunk_data:
        return "!!! MODO DEPURACIÓN ACTIVADO !!!\nDile al usuario: La base de datos tiene 0 chunks con embeddings."

    # 3. Preparar vectores para cálculo masivo
    ids, embeddings, doc_names, indices = zip(*chunk_data)
    
    # Convertir a matriz numpy de forma eficiente
    # Si los embeddings ya son listas (JSONField), no necesitamos json.loads
    try:
        if isinstance(embeddings[0], str):
            # Formato antiguo/corrupto: string de JSON
            matrix = np.array([json.loads(e) for e in embeddings], dtype=np.float32)
        else:
            # Formato correcto: lista de floats
            matrix = np.array(embeddings, dtype=np.float32)
    except Exception as e:
        return f"!!! MODO DEPURACIÓN ACTIVADO !!!\nError cargando matriz: {e}"

    # Vector de consulta
    q_vec = np.array(query_embedding, dtype=np.float32)

    # 4. Cálculo de Similitud Coseno Vectorizada
    # Si los embeddings de OpenAI están normalizados (que lo están), bastaría con el producto punto.
    dot_product = np.dot(matrix, q_vec)
    
    # Para mayor seguridad si no estuvieran normalizados, pero el dot product es la base
    # matrix_norms = np.linalg.norm(matrix, axis=1)
    # query_norm = np.linalg.norm(q_vec)
    # similarities = dot_product / (matrix_norms * query_norm + 1e-9)
    
    # Optimizamos asumiendo normalización (estándar de OpenAI)
    similarities = dot_product

    # 5. Lógica de Boosting (Prioridad Normativa)
    # Usamos una búsqueda insensible a guiones/espacios para mayor robustez
    priority_patterns = ["2.-Ley-21809", "Manual-de-cuentas"]
    account_keywords = ["codigo", "cuenta", "item", "clase", "sep", "pie", "801", "802", "803", "804"]
    
    query_lower = query.lower()
    is_account_query = any(k in query_lower for k in account_keywords)
    
    # Crear máscara para archivos prioritarios
    priority_mask = np.zeros(len(doc_names), dtype=bool)
    for pattern in priority_patterns:
        priority_mask |= np.array([pattern in str(d) for d in doc_names])

    # Aplicar Boost Base (10x para documentos críticos)
    similarities[priority_mask] *= 10.0

    # Boost de Precisión Quirúrgica: Si la consulta es sobre cuentas, 
    # darle un extra de 5x a los fragmentos del manual que ya son prioritarios
    if is_account_query:
        similarities[priority_mask] *= 5.0

    # 6. Selección de Top N
    # Obtenemos los índices de los mayores scores
    top_indices = np.argsort(similarities)[::-1][:top_n]
    
    scored_results = []
    for idx in top_indices:
        if similarities[idx] > 0.12: # Threshold
            scored_results.append({
                'id': ids[idx],
                'doc': doc_names[idx],
                'index': indices[idx],
                'score': similarities[idx]
            })

    if not scored_results:
        return "!!! MODO DEPURACIÓN ACTIVADO !!!\nDile al usuario: No se encontraron fragmentos con relevancia suficiente."

    # 7. Expansión por vecindad y Re-obtención de Contenido
    # Para ahorrar RAM no pedimos el 'content' masivamente arriba, lo pedimos ahora solo para el top
    final_chunks = []
    processed_ids = set()

    for item in scored_results:
        # Traer el chunk original y sus vecinos inmediatos para contexto
        neighbors = AIKnowledgeChunk.objects.filter(
            assistant=assistant,
            document_name=item['doc'],
            index__in=[item['index'] - 1, item['index'], item['index'] + 1]
        ).order_by('index')

        for n in neighbors:
            if n.id not in processed_ids:
                processed_ids.add(n.id)
                final_chunks.append(n)

    # Orden final para el prompt
    final_chunks.sort(key=lambda c: (c.document_name or '', c.index or 0))

    return "\n\n---\n\n".join(
        [f"[Fuente: {c.document_name} - Sec: {c.index}]\n{c.content}" for c in final_chunks]
    )
