"""
Generador de pruebas SIMCE usando DeepSeek + contexto oficial MINEDUC.
Flujo: genera textos → valida extensión → genera preguntas por texto → valida rúbrica.
"""
import json
import os
import re
import random
from pathlib import Path
from openai import OpenAI

DEEPSEEK_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
client = OpenAI(api_key=DEEPSEEK_KEY, base_url='https://api.deepseek.com')

BASE_DIR = Path(__file__).resolve().parent.parent
CONTEXT_FILE = BASE_DIR / 'simce_docs' / 'contexto_oficial.json'

TIPOS_POR_ASIGNATURA = {
    'lenguaje':   ['cuento', 'fabula', 'noticia', 'reportaje', 'carta_formal',
                   'carta_director', 'carta_informal', 'soneto', 'oda',
                   'discontinuo', 'infografia', 'instructivo', 'afiche'],
    'matematica': ['discontinuo', 'infografia', 'instructivo', 'noticia', 'reportaje'],
    'ciencias':   ['articulo_cient', 'discontinuo', 'infografia', 'instructivo',
                   'noticia', 'reportaje', 'receta'],
    'historia':   ['noticia', 'reportaje', 'carta_formal', 'carta_director',
                   'discontinuo', 'infografia', 'afiche'],
}

HABILIDADES_POR_ASIGNATURA = {
    'lenguaje': [
        'Localizar información explícita',
        'Inferir información implícita',
        'Interpretar lenguaje figurado',
        'Identificar propósito comunicativo',
        'Relacionar información de distintas partes del texto',
        'Evaluar y reflexionar sobre el contenido',
        'Reconocer estructura del tipo textual',
        'Comprender vocabulario en contexto',
    ],
    'matematica': [
        'Resolver problemas numéricos',
        'Interpretar datos estadísticos',
        'Aplicar proporcionalidad',
        'Razonar geométricamente',
        'Modelar situaciones matemáticas',
    ],
    'ciencias': [
        'Describir fenómenos naturales',
        'Interpretar resultados experimentales',
        'Relacionar causa y efecto',
        'Aplicar conceptos científicos',
        'Evaluar información científica',
    ],
    'historia': [
        'Identificar causas y consecuencias',
        'Analizar fuentes históricas',
        'Ubicar en tiempo y espacio',
        'Comparar perspectivas',
        'Evaluar procesos históricos',
    ],
}


def load_context():
    """Carga el contexto oficial del MINEDUC."""
    if not CONTEXT_FILE.exists():
        return ""
    with open(CONTEXT_FILE) as f:
        data = json.load(f)
    # Combinar fragmentos relevantes (primeros 15k chars de cada doc)
    ctx = ""
    for key, val in data.items():
        ctx += f"\n\n=== {key} ===\n{val['text'][:15000]}"
    return ctx


def generar_prueba_completa(asignatura, curso, titulo=None):
    """
    Genera una prueba SIMCE completa.
    Retorna dict con textos y preguntas, o lanza excepción con el error.
    """
    context = load_context()
    tipos_disponibles = TIPOS_POR_ASIGNATURA.get(asignatura, TIPOS_POR_ASIGNATURA['lenguaje'])
    tipos_seleccionados = random.sample(tipos_disponibles, min(6, len(tipos_disponibles)))
    habilidades = HABILIDADES_POR_ASIGNATURA.get(asignatura, HABILIDADES_POR_ASIGNATURA['lenguaje'])

    # ── Paso 1: Generar los 6 textos ──────────────────────────────
    prompt_textos = f"""Eres un experto en evaluación educativa SIMCE, psicometría y Bases Curriculares de Chile (Decreto 439/2012).

CONTEXTO OFICIAL MINEDUC (usa esto como referencia de calidad y estilo):
{context[:20000]}

TAREA: Genera exactamente 6 textos auténticos para una prueba tipo SIMCE.
- Asignatura: {asignatura.upper()}
- Nivel: {curso}
- Tipos textuales a usar (en este orden): {', '.join(tipos_seleccionados)}

REQUISITOS CRÍTICOS POR TEXTO:
1. Mínimo 1500 caracteres SIN contar espacios (es un requisito de validez del instrumento)
2. Auténtico: no repetir textos conocidos, crear contenido original
3. Apropiado para el nivel cognitivo de {curso}
4. Respetar la estructura clásica del tipo textual
5. Vocabulario alineado con Bases Curriculares

Responde SOLO con JSON válido, sin texto adicional:
{{
  "textos": [
    {{
      "orden": 1,
      "tipo_textual": "cuento",
      "titulo": "Título del texto",
      "contenido": "Texto completo aquí..."
    }}
  ]
}}"""

    resp_textos = client.chat.completions.create(
        model='deepseek-chat',
        messages=[{'role': 'user', 'content': prompt_textos}],
        max_tokens=8000,
        temperature=0.7,
    )

    raw_textos = resp_textos.choices[0].message.content.strip()
    raw_textos = re.sub(r'^```json\s*', '', raw_textos)
    raw_textos = re.sub(r'\s*```$', '', raw_textos)
    data_textos = json.loads(raw_textos)

    # Validar extensión — si alguno no cumple, regenerar ese texto
    textos_validados = []
    for t in data_textos['textos']:
        chars = len(t['contenido'].replace(' ', ''))
        if chars < 1500:
            t = _regenerar_texto(t, asignatura, curso, context)
        t['char_count'] = len(t['contenido'].replace(' ', ''))
        textos_validados.append(t)

    # ── Paso 2: Generar 5 preguntas por texto (30 total) ─────────
    # Distribución: 20 avanzadas (nivel 3), 5 intermedias (2), 5 iniciales (1)
    # Asignamos: textos 1-4 → 4 avanzadas + 1 otro; textos 5-6 → mix
    niveles_por_texto = _distribuir_niveles()
    alternativas_correctas_pool = _pool_alternativas_correctas()

    textos_con_preguntas = []
    for idx, texto in enumerate(textos_validados):
        niveles = niveles_por_texto[idx]
        prompt_preguntas = f"""Eres un experto en construcción de ítems SIMCE alineados con Bases Curriculares Chile.

TEXTO DE REFERENCIA:
Tipo: {texto['tipo_textual']}
Título: {texto['titulo']}
Contenido:
{texto['contenido']}

TAREA: Crea exactamente 5 preguntas de selección múltiple para este texto.
Niveles asignados para estas 5 preguntas: {niveles}

REGLAS OBLIGATORIAS:
- 4 alternativas por pregunta (A, B, C, D), solo una correcta
- Distractores coherentes con el texto y de extensión similar a la correcta
- Alternativas correctas PRE-ASIGNADAS para estas preguntas: {alternativas_correctas_pool[idx]}
  (debes usar exactamente estas letras como correctas, en ese orden)
- Habilidades a evaluar (varía entre preguntas): {', '.join(habilidades[:5])}
- Nivel 1=inicial, 2=intermedio, 3=avanzado
- Justifica cada nivel y habilidad brevemente

Responde SOLO con JSON válido:
{{
  "preguntas": [
    {{
      "enunciado": "¿Pregunta...?",
      "nivel": 3,
      "habilidad": "Nombre habilidad",
      "habilidad_justificacion": "Por qué evalúa esta habilidad...",
      "nivel_justificacion": "Por qué es nivel avanzado...",
      "alternativa_correcta": "B",
      "pista_1": "Pista sutil que orienta sin revelar la respuesta (1 oración). Ej: 'Fíjate en lo que el autor dice al inicio del segundo párrafo.'",
      "pista_2": "Pista más directa pero que aún requiere que el estudiante razone (1 oración). Ej: 'La respuesta está relacionada con el propósito que tiene el autor al escribir este texto.'",
      "alternativas": [
        {{"letra": "A", "texto": "...", "es_correcta": false, "justificacion": "Es incorrecta porque..."}},
        {{"letra": "B", "texto": "...", "es_correcta": true,  "justificacion": "Es correcta porque..."}},
        {{"letra": "C", "texto": "...", "es_correcta": false, "justificacion": "Es incorrecta porque..."}},
        {{"letra": "D", "texto": "...", "es_correcta": false, "justificacion": "Es incorrecta porque..."}}
      ]
    }}
  ]
}}"""

        resp_preguntas = client.chat.completions.create(
            model='deepseek-chat',
            messages=[{'role': 'user', 'content': prompt_preguntas}],
            max_tokens=4000,
            temperature=0.5,
        )

        raw_p = resp_preguntas.choices[0].message.content.strip()
        raw_p = re.sub(r'^```json\s*', '', raw_p)
        raw_p = re.sub(r'\s*```$', '', raw_p)
        data_p = json.loads(raw_p)

        textos_con_preguntas.append({**texto, 'preguntas': data_p['preguntas']})

    # ── Paso 3: Rúbrica de validación ─────────────────────────────
    rubrica = _validar_rubrica(textos_con_preguntas)

    return {
        'titulo': titulo or f"Ensayo SIMCE {asignatura.title()} {curso}",
        'textos': textos_con_preguntas,
        'rubrica': rubrica,
    }


def _regenerar_texto(texto_original, asignatura, curso, context):
    """Regenera un texto que no cumple la extensión mínima."""
    prompt = f"""El siguiente texto tipo {texto_original['tipo_textual']} NO cumple con el mínimo de 1500 caracteres sin espacios.
Reescríbelo completo, más extenso, manteniendo el mismo tipo textual y nivel {curso}.
Asignatura: {asignatura}.

Texto actual (insuficiente):
{texto_original['contenido']}

Responde SOLO con JSON:
{{"tipo_textual": "{texto_original['tipo_textual']}", "titulo": "...", "contenido": "texto completo aquí..."}}"""

    resp = client.chat.completions.create(
        model='deepseek-chat',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=3000,
        temperature=0.6,
    )
    raw = resp.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return {**texto_original, **json.loads(raw)}


def _distribuir_niveles():
    """
    Distribuye los 30 niveles entre 6 textos (5 preguntas c/u).
    Total: 20 avanzadas (3), 5 intermedias (2), 5 iniciales (1).
    """
    niveles_totales = [3]*20 + [2]*5 + [1]*5
    random.shuffle(niveles_totales)
    return [niveles_totales[i*5:(i+1)*5] for i in range(6)]


def _pool_alternativas_correctas():
    """
    Genera pool de alternativas correctas con distribución 25% cada letra.
    30 preguntas → 7-8 por letra.
    """
    pool = ['A']*8 + ['B']*8 + ['C']*7 + ['D']*7
    random.shuffle(pool)
    return [pool[i*5:(i+1)*5] for i in range(6)]


def _validar_rubrica(textos_con_preguntas):
    """Valida el instrumento contra la rúbrica oficial."""
    rubrica = {
        'criterios': {},
        'aprobado': True,
        'observaciones': [],
    }

    # 1. Estructura: 6 textos
    n_textos = len(textos_con_preguntas)
    ok = n_textos == 6
    rubrica['criterios']['estructura_textos'] = {'ok': ok, 'detalle': f'{n_textos}/6 textos'}
    if not ok:
        rubrica['aprobado'] = False
        rubrica['observaciones'].append(f'Se esperaban 6 textos, se generaron {n_textos}')

    # 2. Tipos textuales únicos
    tipos = [t['tipo_textual'] for t in textos_con_preguntas]
    tipos_unicos = len(set(tipos)) == len(tipos)
    rubrica['criterios']['tipos_unicos'] = {'ok': tipos_unicos, 'detalle': str(tipos)}
    if not tipos_unicos:
        rubrica['aprobado'] = False
        rubrica['observaciones'].append('Hay tipos textuales repetidos')

    # 3. Extensión mínima
    ext_ok = all(len(t['contenido'].replace(' ', '')) >= 1500 for t in textos_con_preguntas)
    detalles_ext = [f"T{t['orden']}: {len(t['contenido'].replace(' ',''))} chars" for t in textos_con_preguntas]
    rubrica['criterios']['extension_minima'] = {'ok': ext_ok, 'detalle': ', '.join(detalles_ext)}
    if not ext_ok:
        rubrica['aprobado'] = False
        rubrica['observaciones'].append('Uno o más textos no alcanzan 1500 caracteres sin espacios')

    # 4. Total de preguntas y distribución por nivel
    todas_preguntas = [p for t in textos_con_preguntas for p in t['preguntas']]
    total_p = len(todas_preguntas)
    niveles = [p['nivel'] for p in todas_preguntas]
    n1 = niveles.count(1)
    n2 = niveles.count(2)
    n3 = niveles.count(3)
    ok_niveles = (total_p == 30 and n3 == 20 and n2 == 5 and n1 == 5)
    rubrica['criterios']['distribucion_niveles'] = {
        'ok': ok_niveles,
        'detalle': f'Total:{total_p} | Avanzado:{n3}/20 | Intermedio:{n2}/5 | Inicial:{n1}/5'
    }
    if not ok_niveles:
        rubrica['aprobado'] = False
        rubrica['observaciones'].append('Distribución de niveles incorrecta')

    # 5. Distribución de alternativas correctas
    letras = [p['alternativa_correcta'] for p in todas_preguntas]
    dist = {l: letras.count(l) for l in ['A', 'B', 'C', 'D']}
    ok_dist = all(6 <= v <= 9 for v in dist.values())
    rubrica['criterios']['distribucion_alternativas'] = {
        'ok': ok_dist,
        'detalle': f"A:{dist['A']} B:{dist['B']} C:{dist['C']} D:{dist['D']} (objetivo: ~25% cada una)"
    }
    if not ok_dist:
        rubrica['aprobado'] = False
        rubrica['observaciones'].append('Distribución de alternativas correctas desbalanceada')

    # 6. Cobertura de habilidades (al menos 4 distintas)
    habilidades = list(set(p['habilidad'] for p in todas_preguntas))
    ok_hab = len(habilidades) >= 4
    rubrica['criterios']['cobertura_habilidades'] = {
        'ok': ok_hab,
        'detalle': f'{len(habilidades)} habilidades distintas: {", ".join(habilidades[:5])}'
    }
    if not ok_hab:
        rubrica['observaciones'].append('Poca variedad de habilidades evaluadas')

    return rubrica
