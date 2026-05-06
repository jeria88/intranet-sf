from django.contrib import admin
from .models import Prueba, TextoPrueba, Pregunta, Alternativa, SesionEstudiante, RespuestaEstudiante


class TextoInline(admin.TabularInline):
    model = TextoPrueba
    extra = 0
    fields = ('orden', 'tipo_textual', 'titulo', 'char_count')
    readonly_fields = ('char_count',)


class PreguntaInline(admin.TabularInline):
    model = Pregunta
    extra = 0
    fields = ('orden', 'nivel', 'habilidad', 'alternativa_correcta', 'enunciado')


@admin.register(Prueba)
class PruebaAdmin(admin.ModelAdmin):
    list_display  = ('titulo', 'asignatura', 'curso', 'anio', 'estado', 'rubrica_ok', 'creada_en')
    list_filter   = ('estado', 'asignatura', 'curso', 'rubrica_ok')
    search_fields = ('titulo',)
    inlines       = [TextoInline]
    readonly_fields = ('creada_en', 'aprobada_en', 'rubrica_log')


@admin.register(TextoPrueba)
class TextoAdmin(admin.ModelAdmin):
    list_display = ('prueba', 'orden', 'tipo_textual', 'titulo', 'char_count')
    inlines      = [PreguntaInline]


@admin.register(SesionEstudiante)
class SesionAdmin(admin.ModelAdmin):
    list_display  = ('nombre', 'rut', 'prueba', 'establecimiento', 'curso', 'puntaje_simce', 'completada')
    list_filter   = ('completada', 'establecimiento', 'prueba')
    search_fields = ('nombre', 'rut')
