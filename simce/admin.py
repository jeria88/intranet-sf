from django.contrib import admin
from .models import (
    Prueba, PruebaTexto, TextoBiblioteca, PreguntaBanco,
    Pregunta, Alternativa, SesionEstudiante, RespuestaEstudiante,
)


class PruebaTextoInline(admin.TabularInline):
    model = PruebaTexto
    extra = 0
    fields = ('orden', 'texto', 'n_nivel1', 'n_nivel2', 'n_nivel3')
    raw_id_fields = ('texto',)


class PreguntaInline(admin.TabularInline):
    model = Pregunta
    extra = 0
    fields = ('orden', 'nivel', 'habilidad', 'alternativa_correcta', 'enunciado')


@admin.register(Prueba)
class PruebaAdmin(admin.ModelAdmin):
    list_display   = ('titulo', 'asignatura', 'curso', 'anio', 'estado', 'rubrica_ok', 'creada_en')
    list_filter    = ('estado', 'asignatura', 'curso', 'rubrica_ok')
    search_fields  = ('titulo',)
    inlines        = [PruebaTextoInline]
    readonly_fields = ('creada_en', 'aprobada_en', 'rubrica_log')


@admin.register(TextoBiblioteca)
class TextoBibliotecaAdmin(admin.ModelAdmin):
    list_display  = ('titulo', 'asignatura', 'tipo_textual', 'dificultad', 'estado', 'word_count', 'creada_en')
    list_filter   = ('estado', 'asignatura', 'tipo_textual', 'dificultad')
    search_fields = ('titulo',)
    readonly_fields = ('char_count', 'word_count', 'creada_en', 'actualizada_en')


@admin.register(PreguntaBanco)
class PreguntaBancoAdmin(admin.ModelAdmin):
    list_display  = ('texto', 'nivel', 'habilidad', 'alternativa_correcta', 'estado', 'creada_en')
    list_filter   = ('estado', 'nivel', 'texto__asignatura')
    search_fields = ('enunciado', 'habilidad')


@admin.register(SesionEstudiante)
class SesionAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'rut', 'prueba', 'establecimiento', 'curso', 'puntaje_simce', 'completada')
    list_filter   = ('completada', 'establecimiento', 'prueba')
    search_fields = ('nombre', 'rut')
