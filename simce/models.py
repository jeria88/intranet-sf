from django.db import models
from django.conf import settings
from django.utils import timezone


ASIGNATURA_CHOICES = [
    ('lenguaje',   'Lenguaje y Comunicación'),
    ('matematica', 'Matemática'),
    ('ciencias',   'Ciencias Naturales'),
    ('historia',   'Historia, Geografía y Cs. Sociales'),
]

CURSO_CHOICES = [
    ('4B', '4° Básico'),
    ('6B', '6° Básico'),
    ('8B', '8° Básico'),
    ('2M', '2° Medio'),
]

LETRA_CHOICES = [('A','A'), ('B','B'), ('C','C'), ('D','D')]

NIVEL_CHOICES = [
    (1, '⭐ Inicial'),
    (2, '⭐⭐ Intermedio'),
    (3, '⭐⭐⭐ Avanzado'),
]

TIPO_TEXTUAL_CHOICES = [
    ('cuento',         'Cuento'),
    ('fabula',         'Fábula'),
    ('noticia',        'Noticia'),
    ('reportaje',      'Reportaje'),
    ('articulo_cient', 'Artículo Científico'),
    ('receta',         'Receta'),
    ('instructivo',    'Manual / Instructivo'),
    ('afiche',         'Afiche Publicitario'),
    ('soneto',         'Soneto'),
    ('oda',            'Oda'),
    ('discontinuo',    'Texto Informativo Discontinuo'),
    ('infografia',     'Infografía'),
    ('carta_formal',   'Carta Formal'),
    ('carta_director', 'Carta al Director'),
    ('carta_informal', 'Carta Informal'),
]

ALTERNATIVA_CHOICES = [('A','A'), ('B','B'), ('C','C'), ('D','D')]

ESTADO_PRUEBA = [
    ('borrador',  'Borrador'),
    ('revision',  'En Revisión'),
    ('aprobada',  'Aprobada'),
    ('publicada', 'Publicada'),
    ('cerrada',   'Cerrada'),
]


class Prueba(models.Model):
    titulo       = models.CharField(max_length=200, verbose_name='Título')
    asignatura   = models.CharField(max_length=20, choices=ASIGNATURA_CHOICES)
    curso        = models.CharField(max_length=3,  choices=CURSO_CHOICES)
    anio         = models.PositiveSmallIntegerField(default=timezone.now().year, verbose_name='Año')
    estado       = models.CharField(max_length=12, choices=ESTADO_PRUEBA, default='borrador')
    creada_por   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, related_name='pruebas_simce')
    creada_en    = models.DateTimeField(auto_now_add=True)
    aprobada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='pruebas_aprobadas')
    aprobada_en  = models.DateTimeField(null=True, blank=True)
    # Rubrica de validación (se llena al generar)
    rubrica_ok   = models.BooleanField(default=False, verbose_name='Rúbrica superada')
    rubrica_log  = models.JSONField(default=dict, verbose_name='Detalle rúbrica')
    # Prompt usado para generación (trazabilidad)
    prompt_usado = models.TextField(blank=True, verbose_name='Prompt de generación')

    class Meta:
        verbose_name = 'Prueba SIMCE'
        verbose_name_plural = 'Pruebas SIMCE'
        ordering = ['-creada_en']

    def __str__(self):
        return f"{self.get_asignatura_display()} {self.get_curso_display()} {self.anio} [{self.get_estado_display()}]"

    @property
    def total_preguntas(self):
        return Pregunta.objects.filter(texto__prueba=self).count()

    @property
    def esta_lista_para_publicar(self):
        return self.rubrica_ok and self.estado == 'aprobada'


class TextoPrueba(models.Model):
    prueba       = models.ForeignKey(Prueba, on_delete=models.CASCADE, related_name='textos')
    orden        = models.PositiveSmallIntegerField(verbose_name='Orden (1-6)')
    tipo_textual = models.CharField(max_length=20, choices=TIPO_TEXTUAL_CHOICES)
    titulo       = models.CharField(max_length=200)
    contenido    = models.TextField(verbose_name='Contenido del texto')
    char_count   = models.PositiveIntegerField(default=0, verbose_name='Caracteres sin espacios')

    class Meta:
        ordering = ['orden']
        unique_together = ['prueba', 'orden']
        verbose_name = 'Texto'
        verbose_name_plural = 'Textos'

    def save(self, *args, **kwargs):
        self.char_count = len(self.contenido.replace(' ', ''))
        super().save(*args, **kwargs)

    def cumple_extension(self):
        return self.char_count >= 1500

    def __str__(self):
        return f"Texto {self.orden} — {self.get_tipo_textual_display()} ({self.prueba})"


class Pregunta(models.Model):
    texto     = models.ForeignKey(TextoPrueba, on_delete=models.CASCADE, related_name='preguntas')
    orden     = models.PositiveSmallIntegerField(verbose_name='Orden global (1-30)')
    enunciado = models.TextField(verbose_name='Enunciado de la pregunta')
    nivel     = models.PositiveSmallIntegerField(choices=NIVEL_CHOICES, verbose_name='Nivel de dificultad')
    habilidad = models.CharField(max_length=200, verbose_name='Habilidad que evalúa')
    habilidad_justificacion = models.TextField(blank=True, verbose_name='Justificación habilidad')
    nivel_justificacion     = models.TextField(blank=True, verbose_name='Justificación nivel')
    alternativa_correcta    = models.CharField(max_length=1, choices=ALTERNATIVA_CHOICES,
                                               verbose_name='Alternativa correcta')

    class Meta:
        ordering = ['orden']
        unique_together = ['texto', 'orden']
        verbose_name = 'Pregunta'
        verbose_name_plural = 'Preguntas'

    def __str__(self):
        return f"P{self.orden} [{self.get_nivel_display()}] — {self.enunciado[:60]}"

    def nivel_estrellas(self):
        return '⭐' * self.nivel


class Alternativa(models.Model):
    pregunta  = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='alternativas')
    letra     = models.CharField(max_length=1, choices=ALTERNATIVA_CHOICES)
    texto     = models.TextField(verbose_name='Texto de la alternativa')
    es_correcta      = models.BooleanField(default=False)
    justificacion    = models.TextField(blank=True, verbose_name='Justificación (para pauta)')

    class Meta:
        ordering = ['letra']
        unique_together = ['pregunta', 'letra']
        verbose_name = 'Alternativa'

    def __str__(self):
        return f"{self.letra}{'✓' if self.es_correcta else ''}: {self.texto[:50]}"


# ── Sesión del estudiante ─────────────────────────────────────────

class SesionEstudiante(models.Model):
    prueba          = models.ForeignKey(Prueba, on_delete=models.CASCADE, related_name='sesiones')
    nombre          = models.CharField(max_length=150, verbose_name='Nombre completo')
    rut             = models.CharField(max_length=12, verbose_name='RUT')
    establecimiento = models.CharField(max_length=20, verbose_name='Establecimiento')
    rbd             = models.CharField(max_length=10, verbose_name='RBD', blank=True)
    curso           = models.CharField(max_length=3,  choices=CURSO_CHOICES)
    letra_curso     = models.CharField(max_length=1,  choices=LETRA_CHOICES)
    iniciada_en     = models.DateTimeField(auto_now_add=True)
    finalizada_en   = models.DateTimeField(null=True, blank=True)
    completada      = models.BooleanField(default=False)
    # Puntajes calculados al enviar
    puntaje_bruto   = models.PositiveSmallIntegerField(default=0)
    porcentaje_logro= models.DecimalField(max_digits=5, decimal_places=2, default=0)
    puntaje_simce   = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['-iniciada_en']
        verbose_name = 'Sesión estudiante'
        verbose_name_plural = 'Sesiones estudiantes'

    def __str__(self):
        return f"{self.nombre} ({self.rut}) — {self.prueba}"

    def calcular_puntajes(self):
        respuestas = self.respuestas.select_related('alternativa_elegida', 'pregunta')
        total = respuestas.count()
        correctas = sum(1 for r in respuestas if r.alternativa_elegida and r.alternativa_elegida.es_correcta)
        self.puntaje_bruto    = correctas
        self.porcentaje_logro = round((correctas / total * 100), 2) if total else 0
        # Conversión aproximada a escala SIMCE (150-350 puntos, media ~260)
        self.puntaje_simce    = int(150 + (self.porcentaje_logro / 100) * 200)
        self.finalizada_en    = timezone.now()
        self.completada       = True
        self.save()


class RespuestaEstudiante(models.Model):
    sesion             = models.ForeignKey(SesionEstudiante, on_delete=models.CASCADE, related_name='respuestas')
    pregunta           = models.ForeignKey(Pregunta, on_delete=models.CASCADE)
    alternativa_elegida= models.ForeignKey(Alternativa, on_delete=models.SET_NULL,
                                           null=True, blank=True)
    respondida_en      = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['sesion', 'pregunta']
        verbose_name = 'Respuesta'

    def __str__(self):
        correcta = self.alternativa_elegida.es_correcta if self.alternativa_elegida else False
        return f"P{self.pregunta.orden} → {self.alternativa_elegida.letra if self.alternativa_elegida else '—'} {'✓' if correcta else '✗'}"
