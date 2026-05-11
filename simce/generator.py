"""
Generador SIMCE — nueva arquitectura: TextoBiblioteca + PreguntaBanco + RAG MINEDUC.
"""
import json
import os
import re
import random
from openai import OpenAI

DEEPSEEK_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
client = OpenAI(api_key=DEEPSEEK_KEY, base_url='https://api.deepseek.com')

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
        "1) TITULAR en mayúsculas. "
        "2) BAJADA: subtítulo que amplía el titular. "
        "3) LEAD: primer párrafo que responde QUÉ, QUIÉN, CUÁNDO, DÓNDE y POR QUÉ. "
        "4) CUERPO: desarrollo con más detalles. "
        "5) Mencionar al menos una fuente con nombre. "
        "Lenguaje objetivo, impersonal, sin opinión."
    ),
    'reportaje': (
        "Texto periodístico extenso y analítico. Incluir: "
        "título, subtítulo, introducción, desarrollo con múltiples ángulos, "
        "datos o citas textuales, conclusión reflexiva."
    ),
    'carta_formal': (
        "Formato obligatorio: lugar y fecha · destinatario con cargo · "
        "saludo formal · cuerpo con asunto claro · despedida formal · firma con cargo. "
        "Sin lenguaje coloquial."
    ),
    'carta_director': (
        "Carta al editor. Encabezado 'Carta al Director', referencia al medio, "
        "postura clara con al menos 2 razones, datos del remitente al final."
    ),
    'carta_informal': (
        "Entre personas cercanas. Saludo coloquial, relato personal emotivo, "
        "preguntas al destinatario, despedida afectuosa."
    ),
    'soneto': (
        "OBLIGATORIO: 14 versos en total, CADA VERSO EN SU PROPIA LÍNEA. "
        "2 cuartetos (4v) + 2 tercetos (3v), separados por línea en blanco. "
        "Rima consonante ABBA ABBA en cuartetos. Temática poética elaborada."
    ),
    'oda': (
        "FORMATO POÉTICO OBLIGATORIO: CADA VERSO EN SU PROPIA LÍNEA (no prosa). "
        "Al menos 10 estrofas de 4-6 versos, separadas por línea en blanco. "
        "Tono celebratorio. Lenguaje con metáforas e imágenes sensoriales."
    ),
    'discontinuo': (
        "TEXTO NO LINEAL: combina prosa con al menos DOS de: "
        "tabla Markdown (|Col|Col|), lista numerada o con viñetas, secciones con subtítulos. "
        "Datos organizados y fáciles de navegar."
    ),
    'infografia': (
        "TÍTULO en mayúsculas · 3-5 secciones con subtítulo · "
        "datos numéricos o porcentajes en cada sección · listas (no párrafos) · "
        "sección FUENTE al final."
    ),
    'instructivo': (
        "TÍTULO · sección MATERIALES con cantidades · "
        "PASOS numerados con verbos en IMPERATIVO · "
        "tiempo estimado o resultado esperado."
    ),
    'afiche': (
        "ESLOGAN en mayúsculas · subtítulo · puntos clave (no párrafos) · "
        "llamado a la acción · datos básicos (lugar/fecha/contacto)."
    ),
    'articulo_cient': (
        "Secciones: INTRODUCCIÓN (pregunta de investigación) · METODOLOGÍA · "
        "RESULTADOS (datos concretos) · DISCUSIÓN · CONCLUSIÓN. "
        "Lenguaje científico formal."
    ),
    'receta': (
        "NOMBRE del plato · PORCIONES y TIEMPO · "
        "INGREDIENTES con cantidades exactas · PREPARACIÓN numerada en imperativo."
    ),
}

SUBJECT_CONTEXT = {
    'lenguaje': (
        "Textos auténticos para comprensión lectora. "
        "Los estudiantes leerán y responderán preguntas sobre el texto."
    ),
    'matematica': (
        "CONTEXTOS DE SITUACIÓN PROBLEMÁTICA. No son textos literarios. "
        "Deben presentar datos numéricos, tablas o gráficos que permitan "
        "formular preguntas de cálculo, interpretación y razonamiento matemático."
    ),
    'ciencias': (
        "Fenómenos naturales, experimentos o procesos biológicos/físicos/químicos "
        "según las Bases Curriculares MINEDUC del nivel. "
        "Incluir datos observables y terminología científica básica."
    ),
    'historia': (
        "Eventos históricos, procesos sociales, geográficos o cívicos del temario SIMCE: "
        "historia de Chile, geografía nacional/latinoamericana, convivencia democrática. "
        "Apropiados para el pensamiento histórico del nivel."
    ),
}

COURSE_CONTEXT = {
    '4B': (
        "4° Básico (9-10 años). Vocabulario cotidiano y concreto. "
        "Oraciones simples. Temas cercanos a la experiencia del estudiante."
    ),
    '6B': (
        "6° Básico (11-12 años). Vocabulario más variado, algunos términos técnicos simples. "
        "Oraciones compuestas. Abstracción moderada."
    ),
}

CHECKLIST_POR_TIPO = {
    'cuento': [
        {'id': 'personajes', 'texto': 'Los personajes tienen nombre propio y características definidas'},
        {'id': 'estructura', 'texto': 'Tiene inicio, desarrollo (nudo) y desenlace'},
        {'id': 'conflicto',  'texto': 'Hay un conflicto central claro'},
        {'id': 'narrador',   'texto': 'El narrador es identificable y coherente'},
        {'id': 'vocabulario','texto': 'El vocabulario es apropiado para el nivel del curso'},
    ],
    'fabula': [
        {'id': 'animales',  'texto': 'Los personajes son animales con nombre que actúan como humanos'},
        {'id': 'conflicto', 'texto': 'El conflicto tiene una dimensión moral o ética clara'},
        {'id': 'moraleja',  'texto': 'La moraleja está escrita explícitamente al final'},
    ],
    'noticia': [
        {'id': 'titular',  'texto': 'Tiene titular informativo'},
        {'id': 'lead',     'texto': 'El primer párrafo responde: qué, quién, cuándo, dónde, por qué'},
        {'id': 'fuentes',  'texto': 'Menciona fuentes o actores con nombre'},
        {'id': 'objetivo', 'texto': 'El lenguaje es objetivo e impersonal'},
    ],
    'reportaje': [
        {'id': 'tema',      'texto': 'El tema es de interés público y relevante'},
        {'id': 'desarrollo','texto': 'Hay un desarrollo extenso con múltiples ángulos'},
        {'id': 'fuentes',   'texto': 'Menciona múltiples fuentes o perspectivas'},
        {'id': 'conclusion','texto': 'Tiene conclusión o cierre temático'},
    ],
    'oda': [
        {'id': 'versos',   'texto': '⚠ CRÍTICO: Está escrito en VERSOS (cada verso en línea separada)'},
        {'id': 'estrofas', 'texto': 'Los versos se agrupan en estrofas separadas por línea en blanco'},
        {'id': 'tono',     'texto': 'El tono es celebratorio o de admiración'},
        {'id': 'extension','texto': 'Tiene al menos 8 estrofas'},
    ],
    'soneto': [
        {'id': 'versos',    'texto': '⚠ CRÍTICO: Tiene exactamente 14 versos'},
        {'id': 'estructura','texto': '⚠ CRÍTICO: 2 cuartetos + 2 tercetos'},
        {'id': 'rima',      'texto': 'Hay rima consonante identificable'},
    ],
    'carta_formal': [
        {'id': 'encabezado',  'texto': 'Tiene lugar, ciudad y fecha al inicio'},
        {'id': 'destinatario','texto': 'El destinatario tiene nombre y/o cargo'},
        {'id': 'saludo',      'texto': 'Saludo formal'},
        {'id': 'despedida',   'texto': 'Despedida formal y firma'},
    ],
    'carta_director': [
        {'id': 'referencia', 'texto': 'Se identifica el medio al que se dirige'},
        {'id': 'argumento',  'texto': 'Hay un argumento central y postura clara'},
        {'id': 'evidencia',  'texto': 'Se aportan razones para sustentar la postura'},
        {'id': 'remitente',  'texto': 'Termina con los datos del remitente'},
    ],
    'carta_informal': [
        {'id': 'saludo',    'texto': 'El saludo es coloquial y cercano'},
        {'id': 'tono',      'texto': 'El tono es personal y emotivo'},
        {'id': 'despedida', 'texto': 'La despedida refleja la relación cercana'},
    ],
    'discontinuo': [
        {'id': 'no_lineal', 'texto': '⚠ CRÍTICO: Incluye elementos no lineales (tablas, listas, esquemas)'},
        {'id': 'datos',     'texto': 'Los datos están organizados claramente'},
    ],
    'infografia': [
        {'id': 'secciones',    'texto': 'Tiene secciones con subtítulos claros'},
        {'id': 'estadisticas', 'texto': 'Incluye estadísticas o datos numéricos'},
        {'id': 'fuente',       'texto': 'Menciona la fuente de los datos'},
    ],
    'instructivo': [
        {'id': 'materiales', 'texto': 'Lista materiales con cantidades'},
        {'id': 'pasos',      'texto': 'Los pasos están numerados'},
        {'id': 'imperativos','texto': 'Usa verbos en imperativo'},
    ],
    'afiche': [
        {'id': 'titulo',  'texto': 'Tiene eslogan llamativo'},
        {'id': 'mensaje', 'texto': 'El mensaje central es claro'},
        {'id': 'cta',     'texto': 'Incluye un llamado a la acción'},
    ],
    'articulo_cient': [
        {'id': 'pregunta',    'texto': 'Plantea una pregunta de investigación'},
        {'id': 'metodologia', 'texto': 'Describe cómo se realizó el estudio'},
        {'id': 'resultados',  'texto': 'Presenta resultados con datos concretos'},
        {'id': 'conclusion',  'texto': 'Hay una conclusión que responde la pregunta'},
    ],
    'receta': [
        {'id': 'nombre',       'texto': 'El nombre del plato está claro'},
        {'id': 'ingredientes', 'texto': 'Lista ingredientes con cantidades'},
        {'id': 'pasos',        'texto': 'Los pasos están numerados'},
    ],
}


# ── FASE 1: Generar un texto para la Biblioteca ───────────────────

def generar_texto_biblioteca(asignatura, tipo_textual, dificultad, curso):
    """
    Genera UN texto y lo guarda como TextoBiblioteca (estado='pendiente').
    Retorna el objeto TextoBiblioteca creado.
    """
    from .models import TextoBiblioteca
    from .rag import buscar_contexto_simce

    context_rag = buscar_contexto_simce(asignatura, tipo_textual, n=4)
    spec         = FORMAT_SPECS.get(tipo_textual, 'Respetar la estructura clásica del tipo textual.')
    subject_ctx  = SUBJECT_CONTEXT.get(asignatura, '')
    course_ctx   = COURSE_CONTEXT.get(curso, COURSE_CONTEXT['6B'])
    dif_labels   = {1: 'Básico', 2: 'Intermedio', 3: 'Avanzado'}

    prompt = f"""Eres un experto en evaluación educativa SIMCE y Bases Curriculares de Chile.

CONTEXTO OFICIAL MINEDUC:
{context_rag}

ASIGNATURA: {asignatura.upper()} — {subject_ctx}
NIVEL DEL CURSO: {course_ctx}
DIFICULTAD DEL TEXTO: {dif_labels.get(dificultad, 'Intermedio')}

TAREA: Genera UN texto tipo '{tipo_textual}' para una prueba tipo SIMCE.

ESPECIFICACIONES DEL TIPO TEXTUAL:
{spec}

REQUISITOS:
- Mínimo 1500 caracteres sin espacios (requisito de validez SIMCE).
- Contenido original, no extraído de textos conocidos.
- Alineado con Bases Curriculares y temario SIMCE de la asignatura.
- Para textos poéticos (oda, soneto): OBLIGATORIO usar versos en líneas separadas, NO prosa.

Responde SOLO con JSON válido:
{{"titulo": "Título del texto", "contenido": "Texto completo aquí..."}}"""

    resp = client.chat.completions.create(
        model='deepseek-chat',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=5000,
        temperature=0.7,
    )
    raw = _clean_json(resp.choices[0].message.content)
    data = json.loads(raw)

    contenido = data['contenido']
    if len(contenido.replace(' ', '')) < 1500:
        contenido = _ampliar_texto(contenido, tipo_textual, asignatura, curso)

    checklist = CHECKLIST_POR_TIPO.get(tipo_textual, [])

    obj = TextoBiblioteca.objects.create(
        asignatura=asignatura,
        tipo_textual=tipo_textual,
        titulo=data.get('titulo', 'Sin título'),
        contenido=contenido,
        dificultad=dificultad,
        estado='pendiente',
        checklist_admin={item['id']: False for item in checklist},
    )
    return obj


def generar_lote_textos_biblioteca(asignatura, curso, n=6):
    """
    Genera N textos para la biblioteca para una asignatura/curso.
    Retorna lista de TextoBiblioteca. Puede lanzar excepción.
    """
    tipos_disponibles = TIPOS_POR_ASIGNATURA.get(asignatura, TIPOS_POR_ASIGNATURA['lenguaje'])
    tipos = random.sample(tipos_disponibles, min(n, len(tipos_disponibles)))
    if len(tipos) < n:
        extras = random.choices(tipos_disponibles, k=n - len(tipos))
        tipos += extras

    dificultades = [1] * (n // 3) + [2] * (n // 3) + [3] * (n - 2 * (n // 3))
    random.shuffle(dificultades)

    resultados = []
    for tipo, dif in zip(tipos, dificultades):
        obj = generar_texto_biblioteca(asignatura, tipo, dif, curso)
        resultados.append(obj)
    return resultados


# ── FASE 2: Generar preguntas para un texto del banco ─────────────

def generar_preguntas_banco(texto_obj, n_nivel1=1, n_nivel2=2, n_nivel3=3):
    """
    Genera preguntas para un TextoBiblioteca y las guarda en PreguntaBanco.
    Retorna lista de PreguntaBanco creados.
    """
    from .models import PreguntaBanco, AlternativaBanco

    asignatura  = texto_obj.asignatura
    habilidades = HABILIDADES_POR_ASIGNATURA.get(asignatura, HABILIDADES_POR_ASIGNATURA['lenguaje'])
    subject_ctx = SUBJECT_CONTEXT.get(asignatura, '')

    niveles = [1] * n_nivel1 + [2] * n_nivel2 + [3] * n_nivel3
    random.shuffle(niveles)
    n_total = len(niveles)

    alts_correctas = _distribuir_alternativas(n_total)

    prompt = f"""Eres un experto en construcción de ítems SIMCE, Bases Curriculares Chile.

ASIGNATURA: {asignatura.upper()} — {subject_ctx}

TEXTO DE REFERENCIA:
Tipo: {texto_obj.tipo_textual}
Título: {texto_obj.titulo}
Contenido:
{texto_obj.contenido}

TAREA: Crea exactamente {n_total} preguntas de selección múltiple para este texto.
Distribución de niveles: {niveles} (1=Inicial, 2=Intermedio, 3=Avanzado).
Alternativas correctas PRE-ASIGNADAS (en ese orden): {alts_correctas}.

REGLAS:
- 4 alternativas por pregunta (A, B, C, D), solo una correcta.
- Distractores plausibles, similar extensión a la correcta.
- Habilidades variadas de: {', '.join(habilidades)}.
- Para matemática: las preguntas deben requerir cálculo u operaciones sobre los datos del texto.
- Pista 1: orientación sutil sin revelar la respuesta.
- Pista 2: pista más directa pero que aún requiere razonamiento.
- Justifica brevemente habilidad y nivel.

Responde SOLO con JSON válido:
{{"preguntas": [
  {{
    "enunciado": "¿Pregunta...?",
    "nivel": 3,
    "habilidad": "Nombre habilidad",
    "habilidad_justificacion": "...",
    "nivel_justificacion": "...",
    "alternativa_correcta": "B",
    "pista_1": "...",
    "pista_2": "...",
    "alternativas": [
      {{"letra": "A", "texto": "...", "es_correcta": false, "justificacion": "..."}},
      {{"letra": "B", "texto": "...", "es_correcta": true,  "justificacion": "..."}},
      {{"letra": "C", "texto": "...", "es_correcta": false, "justificacion": "..."}},
      {{"letra": "D", "texto": "...", "es_correcta": false, "justificacion": "..."}}
    ]
  }}
]}}"""

    resp = client.chat.completions.create(
        model='deepseek-chat',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=6000,
        temperature=0.5,
    )
    raw = _clean_json(resp.choices[0].message.content)
    data = json.loads(raw)

    creadas = []
    for p in data['preguntas']:
        pregunta_obj = PreguntaBanco.objects.create(
            texto=texto_obj,
            enunciado=p['enunciado'],
            nivel=p['nivel'],
            habilidad=p['habilidad'],
            habilidad_justificacion=p.get('habilidad_justificacion', ''),
            nivel_justificacion=p.get('nivel_justificacion', ''),
            alternativa_correcta=p['alternativa_correcta'],
            pista_1=p.get('pista_1', ''),
            pista_2=p.get('pista_2', ''),
            estado='pendiente',
        )
        for alt in p.get('alternativas', []):
            AlternativaBanco.objects.create(
                pregunta=pregunta_obj,
                letra=alt['letra'],
                texto=alt['texto'],
                es_correcta=alt.get('es_correcta', False),
                justificacion=alt.get('justificacion', ''),
            )
        creadas.append(pregunta_obj)
    return creadas


# ── FASE 3: Crear preguntas del test desde el banco ───────────────

def poblar_preguntas_prueba_texto(prueba_texto_obj):
    """
    Para un PruebaTexto dado, crea Pregunta+Alternativa usando:
    1. Preguntas aprobadas del banco (nivel matching n_nivel1/2/3)
    2. Si faltan, genera nuevas con IA y las añade al banco primero.
    Retorna lista de Pregunta creadas.
    """
    from .models import Pregunta, Alternativa, PreguntaBanco, AlternativaBanco

    texto   = prueba_texto_obj.texto
    n_req   = {1: prueba_texto_obj.n_nivel1, 2: prueba_texto_obj.n_nivel2, 3: prueba_texto_obj.n_nivel3}
    orden_actual = 0
    creadas = []

    for nivel in [1, 2, 3]:
        n = n_req[nivel]
        if n <= 0:
            continue

        banco_qs = PreguntaBanco.objects.filter(
            texto=texto, nivel=nivel, estado='aprobado'
        ).exclude(usos_en_pruebas__prueba_texto__prueba=prueba_texto_obj.prueba).order_by('?')[:n]
        banco_list = list(banco_qs)

        # Si faltan, generar nuevas
        faltantes = n - len(banco_list)
        if faltantes > 0:
            n1 = faltantes if nivel == 1 else 0
            n2 = faltantes if nivel == 2 else 0
            n3 = faltantes if nivel == 3 else 0
            nuevas = generar_preguntas_banco(texto, n1, n2, n3)
            for p in nuevas:
                p.estado = 'aprobado'
                p.save(update_fields=['estado'])
            banco_list += nuevas

        for pregunta_banco in banco_list[:n]:
            orden_actual += 1
            pregunta = Pregunta.objects.create(
                prueba_texto=prueba_texto_obj,
                desde_banco=pregunta_banco,
                orden=orden_actual,
                enunciado=pregunta_banco.enunciado,
                nivel=pregunta_banco.nivel,
                habilidad=pregunta_banco.habilidad,
                habilidad_justificacion=pregunta_banco.habilidad_justificacion,
                nivel_justificacion=pregunta_banco.nivel_justificacion,
                alternativa_correcta=pregunta_banco.alternativa_correcta,
                pista_1=pregunta_banco.pista_1,
                pista_2=pregunta_banco.pista_2,
            )
            for alt_banco in pregunta_banco.alternativas.all():
                Alternativa.objects.create(
                    pregunta=pregunta,
                    letra=alt_banco.letra,
                    texto=alt_banco.texto,
                    es_correcta=alt_banco.es_correcta,
                    justificacion=alt_banco.justificacion,
                )
            creadas.append(pregunta)

    return creadas


# ── Ajuste de texto (largo o dificultad) ─────────────────────────

def ajustar_texto(texto_obj, accion, curso='6B'):
    """
    Ajusta TextoBiblioteca según la acción.
    accion: 'aumentar_largo' | 'disminuir_largo' | 'aumentar_dificultad' | 'disminuir_dificultad'
    Retorna dict con titulo, contenido, char_count, word_count, dificultad.
    """
    tipo       = texto_obj.tipo_textual
    spec       = FORMAT_SPECS.get(tipo, 'Respetar la estructura clásica del tipo textual.')
    asignatura = texto_obj.asignatura
    dif_actual = texto_obj.dificultad
    dif_labels = {1: 'Básico', 2: 'Intermedio', 3: 'Avanzado'}

    if accion == 'aumentar_largo':
        instruccion    = "Reescribe el texto haciéndolo MÁS LARGO (al menos 400 caracteres adicionales)."
        nueva_dif      = dif_actual
    elif accion == 'disminuir_largo':
        instruccion    = "Reescribe el texto MÁS CORTO (mínimo 1500 caracteres sin espacios)."
        nueva_dif      = dif_actual
    elif accion == 'aumentar_dificultad':
        nueva_dif      = min(3, dif_actual + 1)
        instruccion    = f"Reescribe aumentando dificultad a {dif_labels[nueva_dif]}: vocabulario más técnico, oraciones más complejas."
    elif accion == 'disminuir_dificultad':
        nueva_dif      = max(1, dif_actual - 1)
        instruccion    = f"Reescribe reduciendo dificultad a {dif_labels[nueva_dif]}: vocabulario simple, oraciones cortas."
    else:
        raise ValueError(f'Acción desconocida: {accion}')

    prompt = f"""Eres un experto en textos educativos para SIMCE Chile.

TEXTO ORIGINAL (tipo '{tipo}', asignatura {asignatura}):
Título: {texto_obj.titulo}
{texto_obj.contenido}

ESPECIFICACIONES DEL TIPO:
{spec}

INSTRUCCIÓN: {instruccion}

REQUISITOS: Mantener mismo tipo textual y formato. Mínimo 1500 caracteres sin espacios.
Para textos poéticos: mantener formato en VERSOS.

Responde SOLO con JSON:
{{"titulo": "...", "contenido": "...", "dificultad": {nueva_dif}}}"""

    resp = client.chat.completions.create(
        model='deepseek-chat',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=5000,
        temperature=0.6,
    )
    raw    = _clean_json(resp.choices[0].message.content)
    result = json.loads(raw)

    contenido = result['contenido']
    return {
        'titulo':     result.get('titulo', texto_obj.titulo),
        'contenido':  contenido,
        'char_count': len(contenido.replace(' ', '')),
        'word_count': len(contenido.split()),
        'dificultad': result.get('dificultad', nueva_dif),
    }


# ── Validación rúbrica de prueba ──────────────────────────────────

def validar_rubrica_prueba(prueba):
    """Valida la distribución de preguntas de una Prueba. Retorna dict rubrica."""
    from .models import Pregunta

    preguntas = list(Pregunta.objects.filter(prueba_texto__prueba=prueba))
    total     = len(preguntas)
    n_textos  = prueba.prueba_textos.count()
    niveles   = [p.nivel for p in preguntas]
    n1, n2, n3 = niveles.count(1), niveles.count(2), niveles.count(3)
    letras    = [p.alternativa_correcta for p in preguntas]
    dist      = {l: letras.count(l) for l in ['A', 'B', 'C', 'D']}
    habs      = len(set(p.habilidad for p in preguntas))

    rubrica = {
        'criterios': {
            'textos_configurados': {
                'ok': n_textos > 0,
                'detalle': f'{n_textos} texto(s) en la prueba',
            },
            'total_preguntas': {
                'ok': total > 0,
                'detalle': f'Total:{total} | Nivel1:{n1} Nivel2:{n2} Nivel3:{n3}',
            },
            'distribucion_alternativas': {
                'ok': all(v > 0 for v in dist.values()),
                'detalle': f"A:{dist['A']} B:{dist['B']} C:{dist['C']} D:{dist['D']}",
            },
            'cobertura_habilidades': {
                'ok': habs >= 3,
                'detalle': f'{habs} habilidades distintas',
            },
        },
        'aprobado': True,
        'observaciones': [],
    }

    for key, val in rubrica['criterios'].items():
        if not val['ok']:
            rubrica['aprobado'] = False
            rubrica['observaciones'].append(val['detalle'])

    return rubrica


# ── Helpers ───────────────────────────────────────────────────────

def _clean_json(text):
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text


def _ampliar_texto(contenido, tipo_textual, asignatura, curso):
    spec = FORMAT_SPECS.get(tipo_textual, '')
    course_ctx = COURSE_CONTEXT.get(curso, '')
    prompt = (
        f"El texto tipo '{tipo_textual}' para {asignatura}/{curso} tiene menos de 1500 caracteres sin espacios. "
        f"Amplíalo conservando la estructura y tipo.\n\n{spec}\n\nTexto actual:\n{contenido}\n\n"
        "Responde SOLO con JSON: {\"contenido\": \"...\"}"
    )
    resp = client.chat.completions.create(
        model='deepseek-chat',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=4000,
        temperature=0.6,
    )
    raw = _clean_json(resp.choices[0].message.content)
    return json.loads(raw).get('contenido', contenido)


def _distribuir_alternativas(n):
    por_letra = n // 4
    pool = ['A'] * por_letra + ['B'] * por_letra + ['C'] * por_letra + ['D'] * (n - por_letra * 3)
    random.shuffle(pool)
    return pool
