"""
Pobla la base de datos con el marco curricular SIMCE Lenguaje 4° Básico
elaborado por el UTP (tablas de tipos textuales + ejes/habilidades).

Crea SimceDocumento + SimceChunk con embeddings para que el RAG
pueda recuperar este conocimiento al generar textos y preguntas.

Uso:
    python manage.py seed_simce_curriculum
    python manage.py seed_simce_curriculum --force   # re-indexar
"""
from django.core.management.base import BaseCommand

# Contenido curricular extraído de las tablas del UTP ─────────────────────────

CHUNKS_CURRICULUM = [
    # ── Tipos textuales ──────────────────────────────────────────────
    {
        'titulo': 'Tipos textuales literarios — Cuento de autor y Cuento folclórico',
        'contenido': (
            "CUENTO DE AUTOR (Literario — Frecuencia SIMCE: Muy alta)\n"
            "Definición: Narración breve escrita por un autor identificable, con estructura narrativa "
            "clara (inicio, desarrollo, desenlace) y personajes definidos.\n"
            "Partes: Inicio (presentación de personajes y contexto), Desarrollo (conflicto central), "
            "Desenlace (resolución), narrador identificable, ambiente.\n"
            "Preguntas típicas por nivel:\n"
            "  Inicial — Localizar: ¿Cómo se llamaba el personaje principal?\n"
            "  Intermedio — Interpretar (Causa y efecto): ¿Cuál fue la razón principal por la que [personaje] tomó esa decisión?\n"
            "  Avanzado — Reflexionar (Propósito del autor): ¿Cuál es el propósito principal del autor al escribir este cuento?\n\n"
            "CUENTO FOLCLÓRICO O POPULAR (Literario — Frecuencia SIMCE: Muy alta)\n"
            "Definición: Narración tradicional de autor anónimo, transmitida oralmente. Incluye cuentos de hadas y maravillosos.\n"
            "Partes: Inicio típico ('Había una vez…'), desarrollo con elementos mágicos, final feliz, "
            "personajes arquetípicos, estructura repetitiva.\n"
            "Preguntas típicas:\n"
            "  Inicial — Localizar: ¿Qué personaje mágico aparece en el cuento?\n"
            "  Intermedio — Interpretar (Secuencia): ¿Qué ocurrió inmediatamente después de que [evento]?\n"
            "  Avanzado — Interpretar (Idea principal): ¿Cuál resume MEJOR el mensaje global del cuento?"
        ),
    },
    {
        'titulo': 'Tipos textuales literarios — Fábula, Leyenda, Mito',
        'contenido': (
            "FÁBULA (Literario — Frecuencia SIMCE: Media)\n"
            "Definición: Narración breve protagonizada por animales con rasgos humanos, que concluye con moraleja explícita.\n"
            "Partes: Introducción breve, conflicto, moraleja explícita al final, personajes animales, estructura simple.\n"
            "Preguntas típicas:\n"
            "  Inicial — Localizar: ¿Qué animal era el personaje principal?\n"
            "  Intermedio — Interpretar (Lenguaje figurado): Cuando el texto dice que el [animal] 'era muy astuto', ¿qué quiere decir?\n"
            "  Avanzado — Interpretar (Conclusiones): ¿Cuál es la moraleja de esta fábula?\n\n"
            "LEYENDA (Literario — Frecuencia SIMCE: Media)\n"
            "Definición: Relato que mezcla elementos reales y maravillosos, vinculado a un lugar o cultura específica.\n"
            "Partes: Ambientación real, elementos fantásticos, propósito explicativo, transmisión oral, personajes históricos o míticos.\n"
            "Preguntas típicas:\n"
            "  Inicial — Localizar: ¿Dónde ocurren los hechos?\n"
            "  Intermedio — Interpretar (Causa y efecto): ¿Por qué ocurrió [fenómeno] según la leyenda?\n"
            "  Avanzado — Interpretar (Conclusiones): ¿Qué elemento real y qué elemento fantástico se combinan?\n\n"
            "MITO (Literario — Frecuencia SIMCE: Media)\n"
            "Definición: Relato sagrado que explica el origen del mundo o fenómenos naturales, protagonizado por dioses o héroes culturales.\n"
            "Partes: Protagonistas divinos, tiempo remoto, propósito cosmogónico, estructura simbólica.\n"
            "Preguntas típicas:\n"
            "  Inicial — Localizar: ¿Quién era el protagonista del mito?\n"
            "  Intermedio — Interpretar (Causa y efecto): Según el mito, ¿cómo se originó [fenómeno natural]?\n"
            "  Avanzado — Reflexionar (Comparar): ¿En qué se diferencia este mito de una explicación científica?"
        ),
    },
    {
        'titulo': 'Tipos textuales literarios — Poema, Soneto, Oda',
        'contenido': (
            "POEMA (Literario — Frecuencia SIMCE: Alta)\n"
            "Definición: Texto lírico que usa lenguaje especial (ritmo, rima, lenguaje figurado) para expresar emociones o crear imágenes.\n"
            "Partes: Versos, estrofas, rima (asonante o consonante) o verso libre, metáforas, personificaciones, símiles.\n"
            "Preguntas típicas:\n"
            "  Inicial — Localizar: ¿De qué o quién habla principalmente este poema?\n"
            "  Intermedio — Interpretar (Lenguaje figurado): ¿Qué significa la expresión '[metáfora]' en el poema?\n"
            "  Avanzado — Reflexionar (Propósito): ¿Cuál es el propósito principal de este poema?\n\n"
            "SONETO (Literario)\n"
            "14 versos: 2 cuartetos (4v) + 2 tercetos (3v), rima consonante ABBA ABBA. Temática poética elaborada.\n\n"
            "ODA (Literario)\n"
            "Al menos 10 estrofas de 4-6 versos. Tono celebratorio. Metáforas e imágenes sensoriales. "
            "CRÍTICO: formato en versos (cada verso en línea separada), NO prosa."
        ),
    },
    {
        'titulo': 'Tipos textuales no literarios — Artículo informativo y Artículo científico',
        'contenido': (
            "ARTÍCULO INFORMATIVO (No Literario — Frecuencia SIMCE: Muy alta)\n"
            "Definición: Texto expositivo que presenta información objetiva y verificable sobre un tema.\n"
            "Partes: Título, subtítulos, introducción, desarrollo en párrafos, cierre, lenguaje objetivo, vocabulario específico.\n"
            "Preguntas típicas:\n"
            "  Inicial — Localizar: ¿Cuál es el tema principal de este artículo?\n"
            "  Intermedio — Interpretar (Idea principal): ¿Cuál es la idea principal del segundo párrafo?\n"
            "  Avanzado — Reflexionar (Hecho vs opinión): ¿Cuál de estas afirmaciones es un HECHO según el artículo?\n\n"
            "ARTÍCULO CIENTÍFICO DIVULGATIVO (No Literario — Frecuencia SIMCE: Media)\n"
            "Definición: Texto con base en investigación científica, adaptado para niños. Explica fenómenos o descubrimientos.\n"
            "Partes: Título, introducción (pregunta/problema), metodología, resultados (con datos), conclusión, gráficos, glosario.\n"
            "Preguntas típicas:\n"
            "  Inicial — Localizar: ¿Qué fenómeno explica este artículo?\n"
            "  Intermedio — Localizar (Texto discontinuo): Según el gráfico, ¿cuál afirmación es correcta?\n"
            "  Avanzado — Interpretar (Conclusiones): ¿Qué conclusión se puede extraer de los resultados?"
        ),
    },
    {
        'titulo': 'Tipos textuales no literarios — Noticia, Infografía, Instructivos',
        'contenido': (
            "NOTICIA (No Literario — Frecuencia SIMCE: Alta)\n"
            "Definición: Relato breve y objetivo de un suceso actual, con estructura de pirámide invertida.\n"
            "Partes: Titular, bajada, lead (qué/quién/cuándo/dónde/por qué), cuerpo, fuente, fecha.\n"
            "Preguntas típicas:\n"
            "  Inicial — Localizar: Según la noticia, ¿qué ocurrió?\n"
            "  Intermedio — Localizar (Lead): ¿Dónde ocurrieron los hechos?\n"
            "  Avanzado — Reflexionar (Hecho vs opinión): ¿Cuál es una OPINIÓN dentro de la noticia?\n\n"
            "INFOGRAFÍA (No Literario — Frecuencia SIMCE: Media)\n"
            "Definición: Representación visual que combina imágenes, gráficos y textos breves para explicar un tema.\n"
            "Partes: Título, imágenes/ilustraciones, texto breve, gráficos, iconos, flujo secuencial.\n"
            "Preguntas típicas:\n"
            "  Inicial — Localizar (Texto discontinuo): ¿Cuál es el título de esta infografía?\n"
            "  Intermedio — Localizar (Relacionar imagen-texto): ¿Qué explica la imagen junto al texto '[fragmento]'?\n"
            "  Avanzado — Reflexionar (Propósito): ¿Por qué el autor usó infografía en lugar de solo texto?\n\n"
            "INSTRUCCIONES / INSTRUCTIVO (No Literario — Frecuencia SIMCE: Alta)\n"
            "Partes: Título, materiales, pasos numerados con verbos en imperativo, advertencias.\n\n"
            "RECETA DE COCINA (No Literario — Frecuencia SIMCE: Media)\n"
            "Partes: Nombre, porciones, tiempo, ingredientes con cantidades, pasos numerados.\n\n"
            "MANUAL DE INSTRUCCIONES (No Literario — Frecuencia SIMCE: Media)\n"
            "Más extenso. Incluye: portada, índice, advertencias, lista de partes, pasos, solución de problemas, glosario."
        ),
    },
    {
        'titulo': 'Tipos textuales no literarios — Biografía, Carta, Afiche',
        'contenido': (
            "BIOGRAFÍA / RELATO HISTÓRICO (No Literario — Frecuencia SIMCE: Media)\n"
            "Definición: Narración de la vida de una persona real o de un acontecimiento histórico relevante.\n"
            "Partes: Introducción (personaje/hecho), orden cronológico, hitos relevantes, contexto histórico, legado.\n"
            "Preguntas típicas:\n"
            "  Inicial — Localizar: ¿Quién es el personaje principal?\n"
            "  Intermedio — Interpretar (Secuencia): ¿Qué hizo [personaje] antes de [hito]?\n"
            "  Avanzado — Reflexionar (Propósito): ¿Cuál es el propósito principal de esta biografía?\n\n"
            "CARTA FORMAL / INFORMAL (No Literario — Frecuencia SIMCE: Baja — más producción escrita)\n"
            "Partes: Fecha y lugar, saludo, cuerpo, despedida, firma.\n"
            "Formal: lenguaje sin coloquialismos (Estimado…, Atentamente…).\n"
            "Informal: tono personal y emotivo (Querido…, Un abrazo…).\n\n"
            "AFICHE PUBLICITARIO (No Literario — Frecuencia SIMCE: Media)\n"
            "Definición: Texto multimodal con propósito persuasivo.\n"
            "Partes: Imagen central, eslogan/título, cuerpo breve, llamada a la acción, logo, colores impactantes.\n"
            "Preguntas típicas:\n"
            "  Inicial — Localizar: ¿Qué se promociona en el afiche?\n"
            "  Intermedio — Reflexionar (Propósito): ¿Qué pretende lograr el autor?\n"
            "  Avanzado — Reflexionar (Hecho vs opinión): ¿El afiche presenta hechos u opiniones?"
        ),
    },
    # ── Ejes y habilidades ───────────────────────────────────────────
    {
        'titulo': 'Eje SIMCE 1 — LOCALIZAR: habilidades y plantillas de pregunta',
        'contenido': (
            "EJE 1: LOCALIZAR\n"
            "El estudiante localiza información explícita en el texto.\n\n"
            "HABILIDAD: Recordar hechos y detalles\n"
            "  Nivel Inicial: Localiza info explícita muy visible, sin distracciones.\n"
            "  Nivel Intermedio: Localiza info entre otros datos similares.\n"
            "  Nivel Avanzado: Localiza info en textos discontinuos (tablas, infografías).\n"
            "  Plantilla Inicial: 'Según el texto, ¿quién/qué/dónde/cuándo [acción]? a)[correcta] b)[secundario] c)[diferente] d)[no mencionado]'\n"
            "  Plantilla Intermedio: '¿Qué se afirma sobre [tema]? a)[correcta parafraseada] b)[otro párrafo] c)[incorrecta similar] d)[no mencionada]'\n"
            "  Plantilla Avanzado: 'Según la [tabla/gráfico], ¿cuál es correcta? a)[dato correcto] b)[dato incorrecto] c)[otro contexto] d)[no presente]'\n\n"
            "HABILIDAD: Comprender la secuencia (explícita)\n"
            "  Nivel Inicial: Ordena 2 eventos claramente separados.\n"
            "  Nivel Intermedio: Ordena 3-4 eventos con conectores temporales visibles.\n"
            "  Nivel Avanzado: Ordena eventos sin conectores explícitos.\n"
            "  Plantilla Inicial: '¿Qué ocurrió PRIMERO? a)[inicio] b)[medio] c)[final] d)[no ocurre]'\n"
            "  Plantilla Intermedio: '¿Qué ocurrió ANTES de [referencia]? a)[correcto anterior] b)[posterior] c)[otra parte] d)[inventado]'\n"
            "  Plantilla Avanzado: '¿Cuál evento NO podría ocurrir primero sin cambiar el sentido?'"
        ),
    },
    {
        'titulo': 'Eje SIMCE 2 — INTERPRETAR: habilidades y plantillas (parte 1)',
        'contenido': (
            "EJE 2: INTERPRETAR\n"
            "El estudiante construye significado integrando información del texto.\n\n"
            "HABILIDAD: Hallar la idea principal\n"
            "  Plantilla Inicial: '¿De qué trata PRINCIPALMENTE? a)[tema correcto] b)[detalle] c)[no mencionado] d)[menor]'\n"
            "  Plantilla Intermedio: '¿Cuál es la IDEA PRINCIPAL del párrafo [N]? a)[central] b)[apoyo] c)[otro párrafo] d)[no presente]'\n"
            "  Plantilla Avanzado: '¿Cuál resume MEJOR el mensaje global? a)[síntesis completa] b)[solo primer párrafo] c)[solo último] d)[detalle]'\n\n"
            "HABILIDAD: Reconocer causa y efecto\n"
            "  Plantilla Inicial: '¿Por qué [evento]? a)[causa explícita] b)[consecuencia] c)[otra causa] d)[no relacionada]'\n"
            "  Plantilla Intermedio: '¿Cuál es la RAZÓN principal? a)[causa inferida] b)[consecuencia] c)[causa de otro evento] d)[opinión]'\n"
            "  Plantilla Avanzado: 'Cadena completa: a)[A causó B que causó C] b)[parcial] c)[invertida] d)[falsa]'\n\n"
            "HABILIDAD: Comparar y contrastar\n"
            "  Plantilla Inicial: '[E1] y [E2] se parecen en que: a)[semejanza correcta] b)[solo E1] c)[solo E2] d)[ninguno]'\n"
            "  Plantilla Intermedio: '¿Cuál es una DIFERENCIA entre [E1] y [E2]? a)[diferencia correcta] b)[semejanza] c)[otro contexto] d)[no mencionada]'\n"
            "  Plantilla Avanzado: 'Diferencia fundamental en [aspecto]: a)[conceptual profunda] b)[superficial] c)[semejanza] d)[no presente]'\n\n"
            "HABILIDAD: Hacer predicciones\n"
            "  Plantilla Inicial: 'Según el título, ¿qué ocurrirá? a)[lógica] b)[ilógica] c)[sin predicción] d)[ya ocurrido]'\n"
            "  Plantilla Intermedio: '¿Qué es lo MÁS PROBABLE que ocurra después? a)[coherente] b)[ya ocurrió] c)[ilógica] d)[deseo sin base]'\n"
            "  Plantilla Avanzado: 'Si [evento] NO hubiera ocurrido: a)[consecuencia lógica] b)[sin relación] c)[igual] d)[imposible]'"
        ),
    },
    {
        'titulo': 'Eje SIMCE 2 — INTERPRETAR: habilidades y plantillas (parte 2)',
        'contenido': (
            "EJE 2: INTERPRETAR (continuación)\n\n"
            "HABILIDAD: Hallar significado de palabras por contexto\n"
            "  Nivel Inicial: Identifica sinónimos o definiciones en el mismo párrafo.\n"
            "  Nivel Intermedio: Infiere significado usando oraciones cercanas.\n"
            "  Nivel Avanzado: Selecciona acepción correcta de palabra con múltiples significados.\n"
            "  Plantilla: '¿Qué significa [palabra] en el texto? a)[correcto del contexto] b)[literal otro contexto] c)[otra palabra] d)[inventado]'\n\n"
            "HABILIDAD: Sacar conclusiones y hacer inferencias\n"
            "  Nivel Inicial: Infiere emoción básica de un personaje.\n"
            "  Nivel Intermedio: Infiere características de personalidad.\n"
            "  Nivel Avanzado: Infiere moraleja, enseñanza o tema central.\n"
            "  Plantilla Inicial: '[Personaje] se sentía: a)[emoción correcta inferida] b)[opuesta] c)[no relacionada] d)[textual sin inferir]'\n"
            "  Plantilla Avanzado: 'MEJOR enseñanza del texto: a)[moraleja integrando implícitos] b)[hecho explícito] c)[opinión sin base] d)[de otro texto]'\n\n"
            "HABILIDAD: Interpretar lenguaje figurado\n"
            "  Nivel Inicial: Reconoce que una expresión no es literal.\n"
            "  Nivel Intermedio: Explica metáforas y personificaciones simples.\n"
            "  Nivel Avanzado: Compara uso del lenguaje figurado entre textos.\n"
            "  Plantilla Inicial: 'Cuando dice \"[expresión]\", quiere decir: a)[figurado correcto] b)[literal] c)[otra expresión] d)[opinión]'\n"
            "  Plantilla Avanzado: 'El autor usa \"[lenguaje figurado]\" para: a)[efecto/idea] b)[decorar] c)[confundir] d)[algo literal]'"
        ),
    },
    {
        'titulo': 'Eje SIMCE 3 — REFLEXIONAR: habilidades y plantillas',
        'contenido': (
            "EJE 3: REFLEXIONAR\n"
            "El estudiante evalúa y reflexiona sobre el texto a partir de su experiencia y conocimiento del mundo.\n\n"
            "HABILIDAD: Distinguir entre hecho y opinión\n"
            "  Nivel Inicial: Reconoce hecho simple frente a opinión marcada.\n"
            "  Nivel Intermedio: Distingue entre hechos y opiniones dentro del mismo texto.\n"
            "  Nivel Avanzado: Evalúa si el autor mezcla hechos y opiniones para persuadir.\n"
            "  Plantilla Inicial: '¿Cuál es un HECHO? a)[verificable del texto] b)[opinión] c)[inventada] d)[de otro texto]'\n"
            "  Plantilla Intermedio: '¿Cuál es una OPINIÓN? a)[subjetiva con juicio] b)[dato verificable] c)[hecho científico] d)[sin juicio]'\n"
            "  Plantilla Avanzado: '¿El autor mezcla hechos y opiniones? a)[Sí, para persuadir] b)[No, solo hechos] c)[Sí, pero es error] d)[No, solo opiniones]'\n\n"
            "HABILIDAD: Identificar el propósito del autor\n"
            "  Plantilla Inicial: 'Este texto fue escrito para: a)[correcto según tipo] b)[opuesto al género] c)[sin relación] d)[detalle como propósito]'\n"
            "  Plantilla Intermedio: '¿Cuál es el PROPÓSITO PRINCIPAL? a)[persuadir/informar/entretener inferido] b)[secundario] c)[opuesto] d)[de otro texto]'\n"
            "  Plantilla Avanzado: 'Ante [audiencia diferente], ¿cambia el propósito? a)[No, es inherente] b)[Sí, cambia] c)[Se vuelve confuso] d)[Depende del lector]'\n\n"
            "HABILIDAD: Interpretar ideas implícitas y síntesis\n"
            "  Plantilla Intermedio: '¿De acuerdo con decisión de [personaje]? a)[Sí/No + justificación EN EL TEXTO] b)[solo experiencia] c)[sin justificación] d)[no toma postura]'\n"
            "  Plantilla Avanzado: 'Título \"[X]\", ¿es adecuado? a)[Sí/No + explícita E implícita] b)[solo explícita] c)[solo personal] d)[sin fundamentar]'"
        ),
    },
]


class Command(BaseCommand):
    help = 'Pobla la BD con el marco curricular SIMCE Lenguaje 4° Básico (tablas UTP) como chunks RAG'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Re-indexar aunque ya existan')

    def handle(self, *args, **options):
        from simce.models import SimceDocumento, SimceChunk
        from simce.rag import get_simce_embedding

        force = options['force']

        doc, created = SimceDocumento.objects.get_or_create(
            nombre='Marco Curricular SIMCE Lenguaje 4° Básico (UTP)',
            defaults={'asignatura': 'lenguaje', 'file_path': ''},
        )

        if doc.procesado and not force:
            self.stdout.write(
                self.style.SUCCESS(f'Ya indexado: {doc.nombre} ({doc.n_chunks} chunks). Usa --force para re-indexar.')
            )
            return

        SimceChunk.objects.filter(documento=doc).delete()

        count = 0
        for idx, chunk_data in enumerate(CHUNKS_CURRICULUM):
            contenido = f"[{chunk_data['titulo']}]\n\n{chunk_data['contenido']}"
            self.stdout.write(f'  Generando embedding {idx + 1}/{len(CHUNKS_CURRICULUM)}: {chunk_data["titulo"][:60]}…')
            emb = get_simce_embedding(contenido)
            SimceChunk.objects.create(
                documento=doc,
                asignatura='lenguaje',
                contenido=contenido,
                embedding=emb,
                chunk_index=idx,
            )
            count += 1

        doc.procesado = True
        doc.n_chunks = count
        doc.save(update_fields=['procesado', 'n_chunks'])

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ seed_simce_curriculum completado: {count} chunks indexados para "{doc.nombre}"'
        ))
