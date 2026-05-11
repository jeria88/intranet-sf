"""
Generador de pruebas SIMCE usando DeepSeek + contexto oficial MINEDUC.
Flujo: [Fase 1] generar_textos → admin revisa → [Fase 2] generar_preguntas_para_prueba
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

# ── Tipos disponibles por asignatura ──────────────────────────────
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

# ── Habilidades por asignatura (para preguntas) ───────────────────
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
        'Resolver operaciones numéricas en contexto',
        'Interpretar datos de tablas y gráficos',
        'Aplicar proporcionalidad y fracciones',
        'Razonar sobre figuras y medidas',
        'Modelar situaciones con operaciones matemáticas',
    ],
    'ciencias': [
        'Describir fenómenos naturales',
        'Interpretar resultados experimentales',
        'Relacionar causa y efecto en procesos naturales',
        'Aplicar conceptos científicos del nivel',
        'Evaluar e interpretar información científica',
    ],
    'historia': [
        'Identificar causas y consecuencias de procesos históricos',
        'Analizar e interpretar fuentes históricas y sociales',
        'Ubicar procesos en tiempo y espacio geográfico',
        'Comparar perspectivas de distintos actores',
        'Evaluar el impacto de procesos históricos en la actualidad',
    ],
}

# ── Formato obligatorio por tipo textual ─────────────────────────
FORMAT_SPECS = {
    'cuento': (
        "Estructura obligatoria: INICIO (presentación de personajes con nombre y contexto), "
        "NUDO (conflicto central bien definido), DESENLACE (resolución del conflicto). "
        "Narrador en 3ª o 1ª persona, coherente durante todo el texto. "
        "Personajes con nombre propio y características reconocibles. "
        "Lenguaje narrativo, párrafos bien desarrollados."
    ),
    'fabula': (
        "Personajes: animales con nombre propio que hablan y actúan como humanos. "
        "El conflicto debe tener una dimensión moral o ética clara. "
        "OBLIGATORIO: terminar con la MORALEJA escrita explícitamente así: 'Moraleja: [texto]'. "
        "Tono didáctico, lenguaje accesible al nivel del curso."
    ),
    'noticia': (
        "Formato periodístico estricto: "
        "1) TITULAR en mayúsculas (breve, informativo, llamativo). "
        "2) BAJADA: subtítulo que amplía el titular (1 oración). "
        "3) LEAD: primer párrafo que responde QUÉ, QUIÉN, CUÁNDO, DÓNDE y POR QUÉ. "
        "4) CUERPO: desarrollo de la noticia con más detalles y contexto. "
        "5) Mencionar al menos una fuente con nombre. "
        "Lenguaje objetivo, impersonal, sin opinión."
    ),
    'reportaje': (
        "Texto periodístico extenso y analítico. Incluir: "
        "título llamativo, subtítulo contextualizador, introducción al tema, "
        "desarrollo con múltiples ángulos y perspectivas, datos estadísticos o citas textuales, "
        "conclusión o cierre que invite a reflexionar. "
        "Más extenso y profundo que una noticia. Puede incluir opinión argumentada."
    ),
    'carta_formal': (
        "Formato carta formal obligatorio: "
        "1) Lugar, ciudad y fecha (ej: 'Santiago, 15 de mayo de 2025'). "
        "2) Nombre y cargo del destinatario. "
        "3) Saludo formal: 'Estimado/a Sr./Sra. [cargo]:'. "
        "4) Cuerpo: presentación del remitente, asunto y solicitud o planteamiento. "
        "5) Despedida formal: 'Atentamente,' o 'Sin otro particular,'. "
        "6) Nombre completo y cargo del firmante. "
        "NO usar lenguaje coloquial."
    ),
    'carta_director': (
        "Carta al editor de un periódico o medio de comunicación. Incluir: "
        "encabezado 'Carta al Director' o 'Estimado Director/a:', "
        "referencia explícita al medio o a una nota publicada, "
        "argumento central con una postura clara (a favor o en contra de algo), "
        "al menos 2 razones o evidencias que sustenten la postura, "
        "datos del remitente al final (nombre, ciudad, ocupación). "
        "Tono respetuoso pero firme y argumentativo."
    ),
    'carta_informal': (
        "Carta entre personas con relación cercana (amigos, familiares). "
        "Saludo coloquial y emotivo (Querido/a, Hola, Mi querido/a...). "
        "Contenido: relato personal de experiencias, emociones o noticias del remitente. "
        "Preguntas al destinatario que muestren interés. "
        "Despedida afectuosa (Con cariño, Tu amigo/a, Un abrazo...). "
        "Firma con nombre de pila. Tono cercano, expresivo, uso de lenguaje coloquial apropiado."
    ),
    'soneto': (
        "ESTRUCTURA OBLIGATORIA Y ESTRICTA — verifica antes de finalizar: "
        "— 14 versos en TOTAL, cada uno en su PROPIA LÍNEA. "
        "— 2 CUARTETOS (estrofas de 4 versos cada una, separadas por línea en blanco). "
        "— 2 TERCETOS (estrofas de 3 versos cada una, separadas por línea en blanco). "
        "— Rima consonante: en los cuartetos esquema ABBA ABBA, en los tercetos CDC DCD o similar. "
        "— Los versos deben tener extensión similar (endecasílabos preferentemente). "
        "Temática amorosa, filosófica o de la naturaleza. Lenguaje poético y elaborado."
    ),
    'oda': (
        "FORMATO POÉTICO OBLIGATORIO — el texto DEBE estar escrito EN VERSOS: "
        "— Cada verso va en su PROPIA LÍNEA (no escribas párrafos de prosa). "
        "— Los versos se agrupan en ESTROFAS separadas por una línea en blanco. "
        "— Escribe al menos 10 estrofas de 4 a 6 versos cada una. "
        "— Tono celebratorio o laudatorio: el poema exalta o alaba un objeto, persona, lugar o idea. "
        "— Usa lenguaje poético: metáforas, personificaciones, imágenes sensoriales. "
        "— EJEMPLO de formato correcto:\n"
        "  Oh, pequeño río\n"
        "  que corres entre piedras,\n"
        "  tu canción de agua\n"
        "  nunca termina.\n\n"
        "  [siguiente estrofa...]"
    ),
    'discontinuo': (
        "TEXTO NO LINEAL: combina información escrita con elementos visuales representados en texto. "
        "OBLIGATORIO incluir al menos DOS de los siguientes: "
        "— Tabla (usar formato Markdown: | Col1 | Col2 | \\n|---|---| \\n| dato | dato |), "
        "— Lista numerada o con viñetas, "
        "— Secciones con subtítulos en negrita o mayúsculas. "
        "La información debe organizarse claramente, ser fácil de navegar. "
        "Puede incluir estadísticas, datos, pasos o categorías."
    ),
    'infografia': (
        "Simula una infografía en formato textual. OBLIGATORIO: "
        "— TÍTULO central en mayúsculas. "
        "— 3 a 5 SECCIONES con subtítulo cada una (pueden ir en mayúsculas o negrita). "
        "— Datos numéricos, porcentajes o estadísticas en cada sección. "
        "— Uso de listas o puntos clave (no párrafos largos). "
        "— Sección FUENTE al final indicando de dónde provienen los datos. "
        "Formato sintético y visualmente organizado."
    ),
    'instructivo': (
        "Texto procedimental con estructura clara: "
        "— TÍTULO del procedimiento. "
        "— Sección MATERIALES o INGREDIENTES (lista con cantidades específicas). "
        "— Sección PROCEDIMIENTO o PASOS (pasos numerados, verbos en IMPERATIVO: Corta, Agrega, Mezcla). "
        "— Indicar tiempo estimado, cantidad de porciones o resultado esperado. "
        "Lenguaje claro, preciso, sin ambigüedades. Verbos en modo imperativo."
    ),
    'afiche': (
        "Simula un afiche en formato textual. OBLIGATORIO: "
        "— TÍTULO o ESLOGAN en mayúsculas, breve y llamativo. "
        "— SUBTÍTULO que amplía el mensaje (1-2 oraciones). "
        "— Información organizada en puntos clave (no párrafos). "
        "— LLAMADO A LA ACCIÓN claro (¡Únete!, ¡Participa!, ¡Infórmate!). "
        "— Datos de contacto, lugar/fecha o información del organizador. "
        "Tono persuasivo, lenguaje directo y motivador."
    ),
    'articulo_cient': (
        "Artículo científico escolar con secciones obligatorias: "
        "— INTRODUCCIÓN: contextualiza el tema y plantea la pregunta de investigación. "
        "— METODOLOGÍA: describe cómo se realizó el estudio o experimento. "
        "— RESULTADOS: presenta datos concretos obtenidos (puede incluir tabla de datos). "
        "— DISCUSIÓN: interpreta los resultados. "
        "— CONCLUSIÓN: responde la pregunta inicial y señala implicancias. "
        "Lenguaje científico formal, uso de terminología del nivel, citas de fuentes."
    ),
    'receta': (
        "Formato de receta culinaria: "
        "— NOMBRE del plato destacado. "
        "— PORCIONES y TIEMPO DE PREPARACIÓN. "
        "— INGREDIENTES: lista con cantidades exactas (ej: '2 tazas de harina', '3 huevos'). "
        "— PREPARACIÓN: pasos numerados con verbos en imperativo. "
        "— Puede incluir TIPS o variaciones al final. "
        "Lenguaje claro y preciso."
    ),
}

# ── Contexto específico por asignatura para generación de textos ──
SUBJECT_CONTEXT = {
    'lenguaje': (
        "Los textos son para la asignatura de Lenguaje y Comunicación. "
        "Deben ser textos auténticos de lectura, apropiados para comprensión lectora. "
        "Los estudiantes leerán cada texto y responderán preguntas sobre él."
    ),
    'matematica': (
        "Los textos son CONTEXTOS DE SITUACIÓN PROBLEMÁTICA para Matemáticas. "
        "Deben presentar escenarios con datos numéricos reales y concretos del mundo cotidiano. "
        "Incluir tablas de datos, gráficos (representados textualmente), estadísticas o medidas. "
        "Los textos deben permitir formular preguntas de cálculo, interpretación y razonamiento matemático. "
        "IMPORTANTE: no son textos de lectura literaria; son situaciones con datos para resolver problemas."
    ),
    'ciencias': (
        "Los textos son para Ciencias Naturales. "
        "Deben presentar fenómenos naturales, experimentos, procesos biológicos, físicos o químicos "
        "apropiados para el nivel del curso según las Bases Curriculares del MINEDUC. "
        "Incluir datos observables, relaciones causa-efecto, y terminología científica básica."
    ),
    'historia': (
        "Los textos son para Historia, Geografía y Ciencias Sociales. "
        "Deben abordar eventos históricos, procesos sociales, geográficos o cívicos "
        "del temario SIMCE: historia de Chile, geografía nacional y latinoamericana, "
        "convivencia democrática, derechos y deberes ciudadanos. "
        "Apropiados para el pensamiento histórico del nivel."
    ),
}

# ── Nivel cognitivo según curso ───────────────────────────────────
COURSE_CONTEXT = {
    '4B': (
        "4° Básico (9-10 años). Vocabulario cotidiano y concreto. "
        "Oraciones simples a moderadamente complejas. "
        "Temas cercanos a la experiencia del estudiante. "
        "Dificultad de comprensión: básica a intermedia."
    ),
    '6B': (
        "6° Básico (11-12 años). Vocabulario más variado, algunos términos técnicos simples. "
        "Oraciones compuestas, párrafos con mayor densidad informativa. "
        "Temas que incluyen abstracción moderada. "
        "Dificultad de comprensión: intermedia a avanzada."
    ),
}

# ── Checklists MINEDUC por tipo textual ──────────────────────────
CHECKLIST_POR_TIPO = {
    'cuento': [
        {'id': 'personajes', 'texto': 'Los personajes tienen nombre propio y características definidas'},
        {'id': 'estructura', 'texto': 'Tiene inicio (presentación), desarrollo (nudo) y desenlace'},
        {'id': 'conflicto',  'texto': 'Hay un conflicto central claro y reconocible'},
        {'id': 'narrador',   'texto': 'El narrador es identificable y coherente'},
        {'id': 'vocabulario','texto': 'El vocabulario es apropiado para el nivel del curso'},
        {'id': 'extension',  'texto': 'Extensión suficiente para elaborar 5 preguntas de comprensión'},
    ],
    'fabula': [
        {'id': 'animales',  'texto': 'Los personajes son animales con nombre que actúan como humanos'},
        {'id': 'conflicto', 'texto': 'El conflicto tiene una dimensión moral o ética clara'},
        {'id': 'moraleja',  'texto': 'La moraleja está escrita explícitamente al final'},
        {'id': 'lenguaje',  'texto': 'El lenguaje es simbólico y accesible al nivel del curso'},
    ],
    'noticia': [
        {'id': 'titular',   'texto': 'Tiene un titular informativo y llamativo'},
        {'id': 'lead',      'texto': 'El primer párrafo responde: qué, quién, cuándo, dónde y por qué'},
        {'id': 'piramide',  'texto': 'Estructura pirámide invertida (información más importante primero)'},
        {'id': 'fuentes',   'texto': 'Menciona fuentes o actores con nombre'},
        {'id': 'objetivo',  'texto': 'El lenguaje es objetivo e impersonal (sin opinión)'},
    ],
    'reportaje': [
        {'id': 'tema',      'texto': 'El tema es de interés público y relevante'},
        {'id': 'desarrollo','texto': 'Hay un desarrollo extenso con múltiples ángulos'},
        {'id': 'fuentes',   'texto': 'Se mencionan múltiples fuentes o perspectivas'},
        {'id': 'analisis',  'texto': 'Incluye análisis o interpretación, no solo datos'},
        {'id': 'conclusion','texto': 'Tiene una conclusión o cierre temático'},
    ],
    'oda': [
        {'id': 'versos',    'texto': '⚠ CRÍTICO: Está escrito en VERSOS (cada verso en línea separada)'},
        {'id': 'estrofas',  'texto': '⚠ CRÍTICO: Los versos se agrupan en estrofas separadas por línea en blanco'},
        {'id': 'tono',      'texto': 'El tono es celebratorio, laudatorio o de admiración'},
        {'id': 'lenguaje',  'texto': 'Usa lenguaje poético (metáforas, imágenes, musicalidad)'},
        {'id': 'extension', 'texto': 'Tiene al menos 8 estrofas (extensión suficiente para el SIMCE)'},
    ],
    'soneto': [
        {'id': 'versos',    'texto': '⚠ CRÍTICO: Tiene exactamente 14 versos'},
        {'id': 'estructura','texto': '⚠ CRÍTICO: 2 cuartetos (4 versos c/u) + 2 tercetos (3 versos c/u)'},
        {'id': 'rima',      'texto': 'Hay rima consonante identificable entre los versos'},
        {'id': 'separacion','texto': 'Las estrofas están separadas por línea en blanco'},
    ],
    'carta_formal': [
        {'id': 'encabezado',  'texto': 'Tiene lugar, ciudad y fecha al inicio'},
        {'id': 'destinatario','texto': 'El destinatario tiene nombre y/o cargo'},
        {'id': 'saludo',      'texto': 'El saludo es formal (Estimado/a Sr./Sra./Don/Doña...)'},
        {'id': 'cuerpo',      'texto': 'El cuerpo expone claramente el asunto o solicitud'},
        {'id': 'despedida',   'texto': 'La despedida es formal (Atentamente, Cordialmente...)'},
        {'id': 'firma',       'texto': 'Termina con nombre y cargo del firmante'},
    ],
    'carta_director': [
        {'id': 'referencia',  'texto': 'Se identifica el medio o publicación al que se dirige'},
        {'id': 'argumento',   'texto': 'Hay un argumento central claro y una postura definida'},
        {'id': 'evidencia',   'texto': 'Se aportan razones o evidencias para sustentar la postura'},
        {'id': 'remitente',   'texto': 'Termina con los datos del remitente (nombre, ciudad, ocupación)'},
    ],
    'carta_informal': [
        {'id': 'saludo',    'texto': 'El saludo es coloquial y cercano (Querido/a, Hola, Mi querida...)'},
        {'id': 'tono',      'texto': 'El tono es personal, emotivo y expresivo'},
        {'id': 'relato',    'texto': 'Hay un relato de experiencias, emociones o noticias personales'},
        {'id': 'despedida', 'texto': 'La despedida refleja la relación cercana (Con cariño, Un abrazo...)'},
    ],
    'discontinuo': [
        {'id': 'no_lineal', 'texto': '⚠ CRÍTICO: Incluye elementos no lineales (tablas, listas, esquemas)'},
        {'id': 'combinado', 'texto': 'Combina información escrita con organización visual'},
        {'id': 'datos',     'texto': 'Los datos o información están organizados claramente'},
        {'id': 'legible',   'texto': 'La estructura es comprensible sin necesidad de imágenes reales'},
    ],
    'infografia': [
        {'id': 'secciones',   'texto': 'Tiene secciones con subtítulos claros'},
        {'id': 'estadisticas','texto': 'Incluye estadísticas, porcentajes o datos numéricos'},
        {'id': 'fuente',      'texto': 'Menciona la fuente de los datos'},
        {'id': 'sintesis',    'texto': 'Formato sintético (listas o puntos, no párrafos largos)'},
    ],
    'instructivo': [
        {'id': 'materiales', 'texto': 'Lista materiales, ingredientes o herramientas con cantidades'},
        {'id': 'pasos',      'texto': 'Los pasos están numerados en orden lógico'},
        {'id': 'imperativos','texto': 'Usa verbos en imperativo (Corta, Agrega, Mezcla...)'},
        {'id': 'precision',  'texto': 'Las instrucciones son precisas y sin ambigüedades'},
    ],
    'afiche': [
        {'id': 'titulo',    'texto': 'Tiene un título o eslogan llamativo (breve y en mayúsculas)'},
        {'id': 'mensaje',   'texto': 'El mensaje central es claro y comprensible'},
        {'id': 'cta',       'texto': 'Incluye un llamado a la acción o invitación'},
        {'id': 'info',      'texto': 'Contiene información básica (lugar, fecha, organizador o contacto)'},
    ],
    'articulo_cient': [
        {'id': 'pregunta',    'texto': 'Plantea una pregunta de investigación o hipótesis'},
        {'id': 'metodologia', 'texto': 'Describe cómo se realizó el estudio o experimento'},
        {'id': 'resultados',  'texto': 'Presenta resultados con datos concretos'},
        {'id': 'conclusion',  'texto': 'Hay una conclusión que responde la pregunta inicial'},
        {'id': 'lenguaje',    'texto': 'El lenguaje es científico y formal para el nivel'},
    ],
    'receta': [
        {'id': 'nombre',       'texto': 'El nombre del plato o preparación está claro'},
        {'id': 'ingredientes', 'texto': 'Lista los ingredientes con cantidades específicas'},
        {'id': 'pasos',        'texto': 'Los pasos de preparación están numerados'},
        {'id': 'tiempo',       'texto': 'Indica tiempo de preparación y número de porciones'},
    ],
}


def load_context():
    if not CONTEXT_FILE.exists():
        return ""
    with open(CONTEXT_FILE) as f:
        data = json.load(f)
    ctx = ""
    for key, val in data.items():
        ctx += f"\n\n=== {key} ===\n{val['text'][:15000]}"
    return ctx


# ── FASE 1: Generar solo textos ───────────────────────────────────

def generar_textos(asignatura, curso):
    """
    Fase 1: genera los 6 textos. Retorna lista de dicts o lanza excepción.
    """
    context = load_context()
    tipos_disponibles = TIPOS_POR_ASIGNATURA.get(asignatura, TIPOS_POR_ASIGNATURA['lenguaje'])
    tipos_seleccionados = random.sample(tipos_disponibles, min(6, len(tipos_disponibles)))

    subject_ctx  = SUBJECT_CONTEXT.get(asignatura, '')
    course_ctx   = COURSE_CONTEXT.get(curso, COURSE_CONTEXT['6B'])

    # Construir especificaciones por tipo
    specs_texto = ""
    for i, tipo in enumerate(tipos_seleccionados, 1):
        spec = FORMAT_SPECS.get(tipo, 'Respetar la estructura clásica del tipo textual.')
        specs_texto += f"\nTexto {i} — tipo '{tipo}':\n{spec}\n"

    prompt = f"""Eres un experto en evaluación educativa SIMCE y Bases Curriculares de Chile (Decreto 439/2012).

CONTEXTO OFICIAL MINEDUC:
{context[:18000]}

CONTEXTO DE ASIGNATURA:
{subject_ctx}

NIVEL DEL CURSO:
{course_ctx}

TAREA: Genera exactamente 6 textos auténticos para una prueba tipo SIMCE.
- Asignatura: {asignatura.upper()}
- Nivel: {curso}
- Tipos textuales a usar (en este orden): {', '.join(tipos_seleccionados)}

ESPECIFICACIONES OBLIGATORIAS POR TEXTO:
{specs_texto}

REQUISITOS GENERALES:
1. Mínimo 1500 caracteres SIN contar espacios (requisito de validez del instrumento SIMCE).
2. Contenido original y auténtico, no textos conocidos.
3. Alineado con Bases Curriculares y temario SIMCE de la asignatura.
4. Indicar la dificultad del texto: 1=Básico, 2=Intermedio, 3=Avanzado.

IMPORTANTE: Para textos poéticos (oda, soneto), el contenido DEBE estar en versos separados por salto de línea, NO en prosa. Verifica la estructura antes de incluirlo en el JSON.

Responde SOLO con JSON válido, sin texto adicional:
{{
  "textos": [
    {{
      "orden": 1,
      "tipo_textual": "cuento",
      "titulo": "Título del texto",
      "contenido": "Texto completo aquí...",
      "dificultad": 2
    }}
  ]
}}"""

    resp = client.chat.completions.create(
        model='deepseek-chat',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=9000,
        temperature=0.7,
    )

    raw = resp.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    data = json.loads(raw)

    textos = []
    for t in data['textos']:
        chars = len(t['contenido'].replace(' ', ''))
        if chars < 1500:
            t = _regenerar_texto(t, asignatura, curso)
        t['char_count'] = len(t['contenido'].replace(' ', ''))
        t['word_count'] = len(t['contenido'].split())
        t['dificultad'] = t.get('dificultad', 2)
        textos.append(t)

    return textos


# ── FASE 2: Generar preguntas para textos aprobados ───────────────

def generar_preguntas_para_prueba(prueba, textos_override=None, n_nivel1=5, n_nivel2=5, n_nivel3=20):
    """
    Fase 2: genera preguntas para los textos aprobados de la prueba.
    textos_override: lista de TextoPrueba ya filtrada (si None, usa todos los aprobados).
    n_nivel1/2/3: cantidad total de preguntas por nivel de dificultad.
    Retorna dict con textos+preguntas y rúbrica, o lanza excepción.
    """
    textos_aprobados = textos_override if textos_override is not None else list(
        prueba.textos.filter(estado_texto='aprobado').order_by('orden')
    )
    if not textos_aprobados:
        raise ValueError('No hay textos aprobados para generar preguntas.')

    asignatura = prueba.asignatura
    curso      = prueba.curso
    habilidades = HABILIDADES_POR_ASIGNATURA.get(asignatura, HABILIDADES_POR_ASIGNATURA['lenguaje'])
    subject_ctx = SUBJECT_CONTEXT.get(asignatura, '')

    n_textos = len(textos_aprobados)
    niveles_por_texto        = _distribuir_niveles(n_textos, n_nivel1, n_nivel2, n_nivel3)
    alternativas_correctas_pool = _pool_alternativas_correctas(n_textos)

    preguntas_por_texto = (n_nivel1 + n_nivel2 + n_nivel3) // n_textos if n_textos else 5

    textos_con_preguntas = []
    for idx, texto_obj in enumerate(textos_aprobados):
        niveles = niveles_por_texto[idx]
        tipo    = texto_obj.tipo_textual
        n_pxte  = len(niveles)

        prompt_preguntas = f"""Eres un experto en construcción de ítems SIMCE alineados con Bases Curriculares Chile.

ASIGNATURA: {asignatura.upper()} — {subject_ctx}
NIVEL: {curso}

TEXTO DE REFERENCIA:
Tipo: {tipo}
Título: {texto_obj.titulo}
Contenido:
{texto_obj.contenido}

TAREA: Crea exactamente {n_pxte} preguntas de selección múltiple para este texto.
Niveles asignados para estas {n_pxte} preguntas: {niveles}

REGLAS OBLIGATORIAS:
- 4 alternativas por pregunta (A, B, C, D), solo una correcta.
- Distractores coherentes y plausibles, misma extensión aproximada que la correcta.
- Alternativas correctas PRE-ASIGNADAS: {alternativas_correctas_pool[idx]} (úsalas exactamente en ese orden).
- Habilidades a evaluar (varía entre preguntas): {', '.join(habilidades[:5])}.
- Nivel 1=inicial, 2=intermedio, 3=avanzado.
- Para asignaturas de cálculo (matemática): las preguntas deben requerir operaciones o razonamiento numérico basado en los datos del texto.
- Justifica cada nivel y habilidad brevemente.

Responde SOLO con JSON válido:
{{
  "preguntas": [
    {{
      "enunciado": "¿Pregunta...?",
      "nivel": 3,
      "habilidad": "Nombre habilidad",
      "habilidad_justificacion": "Por qué evalúa esta habilidad...",
      "nivel_justificacion": "Por qué es este nivel...",
      "alternativa_correcta": "B",
      "pista_1": "Pista sutil que orienta sin revelar la respuesta.",
      "pista_2": "Pista más directa que aún requiere razonamiento.",
      "alternativas": [
        {{"letra": "A", "texto": "...", "es_correcta": false, "justificacion": "Es incorrecta porque..."}},
        {{"letra": "B", "texto": "...", "es_correcta": true,  "justificacion": "Es correcta porque..."}},
        {{"letra": "C", "texto": "...", "es_correcta": false, "justificacion": "Es incorrecta porque..."}},
        {{"letra": "D", "texto": "...", "es_correcta": false, "justificacion": "Es incorrecta porque..."}}
      ]
    }}
  ]
}}"""

        resp = client.chat.completions.create(
            model='deepseek-chat',
            messages=[{'role': 'user', 'content': prompt_preguntas}],
            max_tokens=4000,
            temperature=0.5,
        )
        raw_p = resp.choices[0].message.content.strip()
        raw_p = re.sub(r'^```json\s*', '', raw_p)
        raw_p = re.sub(r'\s*```$', '', raw_p)
        data_p = json.loads(raw_p)

        textos_con_preguntas.append({
            'texto_obj': texto_obj,
            'preguntas': data_p['preguntas'],
        })

    rubrica = _validar_rubrica(textos_con_preguntas)
    return {'textos': textos_con_preguntas, 'rubrica': rubrica}


# ── Ajuste de texto (largo o dificultad) ─────────────────────────

def ajustar_texto(texto_obj, accion):
    """
    Ajusta el texto según la acción: aumentar_largo, disminuir_largo,
    aumentar_dificultad, disminuir_dificultad.
    Retorna dict con nuevo contenido, char_count, word_count, dificultad.
    """
    tipo  = texto_obj.tipo_textual
    spec  = FORMAT_SPECS.get(tipo, 'Respetar la estructura clásica del tipo textual.')
    curso = texto_obj.prueba.curso
    asignatura = texto_obj.prueba.asignatura

    dificultad_actual = texto_obj.dificultad
    dificultad_labels = {1: 'Básico', 2: 'Intermedio', 3: 'Avanzado'}

    if accion == 'aumentar_largo':
        instruccion = (
            "Reescribe el texto haciéndolo MÁS LARGO. "
            "Agrega al menos 400 caracteres de contenido nuevo, manteniendo coherencia y calidad. "
            "No cambies el nivel de dificultad."
        )
        nueva_dificultad = dificultad_actual
    elif accion == 'disminuir_largo':
        instruccion = (
            "Reescribe el texto haciéndolo MÁS CORTO (pero sin bajar de 1500 caracteres sin espacios). "
            "Elimina contenido redundante manteniendo la estructura y coherencia del tipo textual. "
            "No cambies el nivel de dificultad."
        )
        nueva_dificultad = dificultad_actual
    elif accion == 'aumentar_dificultad':
        nueva_dificultad = min(3, dificultad_actual + 1)
        instruccion = (
            f"Reescribe el texto aumentando su nivel de dificultad a {dificultad_labels[nueva_dificultad]}. "
            "Usa vocabulario más técnico o especializado, oraciones más complejas, "
            "mayor densidad informativa o mayor abstracción. "
            "Mantén la misma extensión aproximada."
        )
    elif accion == 'disminuir_dificultad':
        nueva_dificultad = max(1, dificultad_actual - 1)
        instruccion = (
            f"Reescribe el texto reduciendo su nivel de dificultad a {dificultad_labels[nueva_dificultad]}. "
            "Simplifica el vocabulario, usa oraciones más cortas y directas, "
            "conceptos más concretos y cercanos a la experiencia del estudiante. "
            "Mantén la misma extensión aproximada."
        )
    else:
        raise ValueError(f'Acción desconocida: {accion}')

    prompt = f"""Eres un experto en textos educativos para SIMCE Chile.

TEXTO ORIGINAL (tipo '{tipo}', nivel {curso}, asignatura {asignatura}):
Título: {texto_obj.titulo}
Contenido actual:
{texto_obj.contenido}

ESPECIFICACIONES DEL TIPO TEXTUAL:
{spec}

INSTRUCCIÓN DE AJUSTE:
{instruccion}

REQUISITOS:
- Mantener el mismo tipo textual y su formato específico obligatorio.
- Mantener el mismo título (o ajustarlo levemente si es necesario).
- Mínimo 1500 caracteres sin espacios.
- Para textos poéticos (oda, soneto): mantener formato en VERSOS, no convertir a prosa.

Responde SOLO con JSON válido:
{{"titulo": "Título del texto", "contenido": "Texto ajustado completo aquí...", "dificultad": {nueva_dificultad}}}"""

    resp = client.chat.completions.create(
        model='deepseek-chat',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=5000,
        temperature=0.6,
    )
    raw = resp.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    result = json.loads(raw)

    contenido = result['contenido']
    return {
        'titulo':     result.get('titulo', texto_obj.titulo),
        'contenido':  contenido,
        'char_count': len(contenido.replace(' ', '')),
        'word_count': len(contenido.split()),
        'dificultad': result.get('dificultad', nueva_dificultad),
    }


# ── Helpers ───────────────────────────────────────────────────────

def _regenerar_texto(texto_original, asignatura, curso):
    tipo = texto_original['tipo_textual']
    spec = FORMAT_SPECS.get(tipo, 'Respetar la estructura clásica del tipo textual.')
    course_ctx = COURSE_CONTEXT.get(curso, COURSE_CONTEXT['6B'])

    prompt = f"""El siguiente texto tipo '{tipo}' NO cumple el mínimo de 1500 caracteres sin espacios.
Reescríbelo completo y más extenso. Asignatura: {asignatura}. {course_ctx}

Especificaciones obligatorias del tipo:
{spec}

Texto actual (insuficiente):
{texto_original['contenido']}

Responde SOLO con JSON:
{{"tipo_textual": "{tipo}", "titulo": "...", "contenido": "texto completo aquí...", "dificultad": 2}}"""

    resp = client.chat.completions.create(
        model='deepseek-chat',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=4000,
        temperature=0.6,
    )
    raw = resp.choices[0].message.content.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return {**texto_original, **json.loads(raw)}


def _distribuir_niveles(n_textos=6, n_nivel1=5, n_nivel2=5, n_nivel3=20):
    total = n_nivel1 + n_nivel2 + n_nivel3
    preguntas_por_texto = total // n_textos if n_textos else 5
    niveles_totales = [3]*n_nivel3 + [2]*n_nivel2 + [1]*n_nivel1
    # Ajustar al múltiplo exacto
    while len(niveles_totales) < n_textos * preguntas_por_texto:
        niveles_totales.append(3)
    niveles_totales = niveles_totales[:n_textos * preguntas_por_texto]
    random.shuffle(niveles_totales)
    return [niveles_totales[i*preguntas_por_texto:(i+1)*preguntas_por_texto]
            for i in range(n_textos)]


def _pool_alternativas_correctas(n_textos=6):
    total = n_textos * 5
    por_letra = total // 4
    pool = ['A']*por_letra + ['B']*por_letra + ['C']*por_letra + ['D']*(total - por_letra*3)
    random.shuffle(pool)
    return [pool[i*5:(i+1)*5] for i in range(n_textos)]


def _validar_rubrica(textos_con_preguntas):
    rubrica = {'criterios': {}, 'aprobado': True, 'observaciones': []}

    n_textos = len(textos_con_preguntas)
    ok = n_textos == 6
    rubrica['criterios']['estructura_textos'] = {'ok': ok, 'detalle': f'{n_textos}/6 textos'}
    if not ok:
        rubrica['aprobado'] = False
        rubrica['observaciones'].append(f'Se esperaban 6 textos aprobados, hay {n_textos}')

    todas_preguntas = [p for t in textos_con_preguntas for p in t['preguntas']]
    total_p = len(todas_preguntas)
    niveles = [p['nivel'] for p in todas_preguntas]
    n1, n2, n3 = niveles.count(1), niveles.count(2), niveles.count(3)
    ok_niveles = (total_p == n_textos * 5)
    rubrica['criterios']['total_preguntas'] = {
        'ok': ok_niveles,
        'detalle': f'Total:{total_p} | Avanzado:{n3} | Intermedio:{n2} | Inicial:{n1}'
    }
    if not ok_niveles:
        rubrica['aprobado'] = False
        rubrica['observaciones'].append(f'Se esperaban {n_textos*5} preguntas, hay {total_p}')

    letras = [p['alternativa_correcta'] for p in todas_preguntas]
    dist   = {l: letras.count(l) for l in ['A', 'B', 'C', 'D']}
    ok_dist = all(v > 0 for v in dist.values())
    rubrica['criterios']['distribucion_alternativas'] = {
        'ok': ok_dist,
        'detalle': f"A:{dist['A']} B:{dist['B']} C:{dist['C']} D:{dist['D']}"
    }
    if not ok_dist:
        rubrica['aprobado'] = False
        rubrica['observaciones'].append('Distribución de alternativas correctas muy desbalanceada')

    habilidades_unicas = len(set(p['habilidad'] for p in todas_preguntas))
    ok_hab = habilidades_unicas >= 3
    rubrica['criterios']['cobertura_habilidades'] = {
        'ok': ok_hab,
        'detalle': f'{habilidades_unicas} habilidades distintas'
    }
    if not ok_hab:
        rubrica['observaciones'].append('Poca variedad de habilidades evaluadas')

    return rubrica
