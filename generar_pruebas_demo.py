"""
Script para generar pruebas SIMCE demo para las 4 asignaturas.
Ejecutar: python generar_pruebas_demo.py
"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))

# Cargar .env manualmente
from pathlib import Path
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, val = line.partition('=')
            # Quitar comentarios inline
            val = val.split('#')[0].strip()
            os.environ.setdefault(key.strip(), val)

django.setup()

from django.contrib.auth import get_user_model
from simce.models import Prueba, TextoPrueba, Pregunta, Alternativa
from simce.generator import generar_prueba_completa

User = get_user_model()

# Usar el primer superusuario como creador
admin = User.objects.filter(is_superuser=True).first()
if not admin:
    admin = User.objects.first()

ASIGNATURAS = ['lenguaje', 'matematica', 'ciencias', 'historia']
CURSOS      = ['4B', '6B', '8B', '2M']

def guardar_prueba(resultado, asignatura, curso, creada_por):
    rubrica = resultado['rubrica']
    prueba = Prueba.objects.create(
        titulo      = resultado['titulo'],
        asignatura  = asignatura,
        curso       = curso,
        estado      = 'revision',
        creada_por  = creada_por,
        rubrica_ok  = rubrica['aprobado'],
        rubrica_log = rubrica,
    )
    orden_global = 1
    for t_data in resultado['textos']:
        texto = TextoPrueba.objects.create(
            prueba       = prueba,
            orden        = t_data['orden'],
            tipo_textual = t_data['tipo_textual'],
            titulo       = t_data['titulo'],
            contenido    = t_data['contenido'],
        )
        for p_data in t_data['preguntas']:
            pregunta = Pregunta.objects.create(
                texto                   = texto,
                orden                   = orden_global,
                enunciado               = p_data['enunciado'],
                nivel                   = p_data['nivel'],
                habilidad               = p_data['habilidad'],
                habilidad_justificacion = p_data.get('habilidad_justificacion', ''),
                nivel_justificacion     = p_data.get('nivel_justificacion', ''),
                alternativa_correcta    = p_data['alternativa_correcta'],
            )
            for a_data in p_data['alternativas']:
                Alternativa.objects.create(
                    pregunta      = pregunta,
                    letra         = a_data['letra'],
                    texto         = a_data['texto'],
                    es_correcta   = a_data['es_correcta'],
                    justificacion = a_data.get('justificacion', ''),
                )
            orden_global += 1
    return prueba


if __name__ == '__main__':
    combos = [(a, c) for a in ASIGNATURAS for c in CURSOS]
    print(f"Generando {len(combos)} pruebas SIMCE demo...\n")

    for asignatura, curso in combos:
        print(f"  → {asignatura.upper()} {curso}...", end=' ', flush=True)
        try:
            resultado = generar_prueba_completa(asignatura, curso)
            prueba    = guardar_prueba(resultado, asignatura, curso, admin)
            rubrica   = prueba.rubrica_ok
            print(f"✓  [{prueba.titulo[:50]}] rubrica={'OK' if rubrica else 'WARN'}")
        except Exception as e:
            print(f"✗  ERROR: {e}")

    print("\nGeneración completada.")
    print(f"Total pruebas en BD: {Prueba.objects.count()}")
