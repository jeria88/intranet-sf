import math
import os
from django.conf import settings


def _cosine(v1, v2):
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    return dot / (n1 * n2) if n1 and n2 else 0.0


def get_simce_embedding(text):
    import openai
    api_key = getattr(settings, 'OPENAI_API_KEY', os.environ.get('OPENAI_API_KEY'))
    if not api_key:
        return None
    try:
        client = openai.OpenAI(api_key=api_key)
        resp = client.embeddings.create(input=[text[:8000]], model='text-embedding-3-small')
        return resp.data[0].embedding
    except Exception as e:
        print(f"[SIMCE RAG] embedding error: {e}")
        return None


def buscar_contexto_simce(asignatura, tipo_textual='', n=5):
    """
    Busca los n chunks más relevantes para asignatura+tipo_textual.
    Devuelve un string listo para incluir en el prompt de IA.
    """
    from .models import SimceChunk

    query = f"Criterios SIMCE para {asignatura}"
    if tipo_textual:
        query += f" texto tipo {tipo_textual}"

    query_vec = get_simce_embedding(query)
    if not query_vec:
        return ""

    # Cargar chunks de asignatura + general
    chunks = list(
        SimceChunk.objects.filter(
            asignatura__in=[asignatura, 'general'],
            embedding__isnull=False,
        ).only('id', 'contenido', 'embedding')
    )
    if not chunks:
        return ""

    scored = []
    for chunk in chunks:
        emb = chunk.embedding
        if isinstance(emb, str):
            import json
            emb = json.loads(emb)
        sim = _cosine(query_vec, emb)
        scored.append((sim, chunk.contenido))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [contenido for _, contenido in scored[:n]]

    return "\n\n---\n\n".join(top)


def indexar_documento(doc_obj):
    """
    Procesa un SimceDocumento: extrae texto del PDF, lo divide en chunks
    y genera embeddings. Actualiza doc_obj.procesado y doc_obj.n_chunks.
    """
    from .models import SimceChunk
    from ai_modules.utils import extract_text_from_pdf

    if not doc_obj.file_path or not os.path.exists(doc_obj.file_path):
        print(f"[SIMCE RAG] archivo no encontrado: {doc_obj.file_path}")
        return False

    try:
        with open(doc_obj.file_path, 'rb') as f:
            texto = extract_text_from_pdf(f)
    except Exception as e:
        print(f"[SIMCE RAG] error leyendo PDF: {e}")
        return False

    if not texto.strip():
        return False

    # Dividir en chunks de ~800 palabras con solapamiento de 80
    palabras = texto.split()
    chunk_size, overlap = 800, 80
    chunks_texto = []
    i = 0
    while i < len(palabras):
        chunk = ' '.join(palabras[i:i + chunk_size])
        chunks_texto.append(chunk)
        i += chunk_size - overlap

    # Eliminar chunks anteriores de este documento
    SimceChunk.objects.filter(documento=doc_obj).delete()

    count = 0
    for idx, contenido in enumerate(chunks_texto):
        emb = get_simce_embedding(contenido)
        SimceChunk.objects.create(
            documento=doc_obj,
            asignatura=doc_obj.asignatura,
            contenido=contenido,
            embedding=emb,
            chunk_index=idx,
        )
        count += 1

    doc_obj.procesado = True
    doc_obj.n_chunks = count
    doc_obj.save(update_fields=['procesado', 'n_chunks'])
    return True
