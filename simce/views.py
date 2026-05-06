import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.views.decorators.http import require_POST

from .models import (Prueba, TextoPrueba, Pregunta, Alternativa,
                     SesionEstudiante, RespuestaEstudiante,
                     ASIGNATURA_CHOICES, CURSO_CHOICES)
from .generator import generar_prueba_completa

is_staff = lambda u: u.is_staff or u.is_superuser


# ── Admin: Dashboard ──────────────────────────────────────────────

@login_required
@user_passes_test(is_staff)
def admin_dashboard(request):
    pruebas = Prueba.objects.all().annotate(
        n_sesiones=Count('sesiones', filter=Q(sesiones__completada=True))
    )
    ctx = {
        'pruebas': pruebas,
        'asignaturas': ASIGNATURA_CHOICES,
        'cursos': CURSO_CHOICES,
    }
    return render(request, 'simce/admin_dashboard.html', ctx)


# ── Admin: Generar prueba con IA ──────────────────────────────────

@login_required
@user_passes_test(is_staff)
@require_POST
def admin_generar(request):
    asignatura = request.POST.get('asignatura')
    curso      = request.POST.get('curso')
    titulo     = request.POST.get('titulo', '').strip() or None

    if not asignatura or not curso:
        messages.error(request, 'Selecciona asignatura y curso.')
        return redirect('simce:admin_dashboard')

    try:
        resultado = generar_prueba_completa(asignatura, curso, titulo)
    except Exception as e:
        messages.error(request, f'Error al generar con IA: {e}')
        return redirect('simce:admin_dashboard')

    # Guardar en BD
    rubrica = resultado['rubrica']
    prueba = Prueba.objects.create(
        titulo      = resultado['titulo'],
        asignatura  = asignatura,
        curso       = curso,
        estado      = 'revision',
        creada_por  = request.user,
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

    messages.success(request, f'Prueba generada: {prueba.titulo}')
    return redirect('simce:admin_revisar', pk=prueba.pk)


# ── Admin: Revisar prueba ─────────────────────────────────────────

@login_required
@user_passes_test(is_staff)
def admin_revisar(request, pk):
    prueba = get_object_or_404(Prueba, pk=pk)
    textos = prueba.textos.prefetch_related('preguntas__alternativas').all()
    ctx = {'prueba': prueba, 'textos': textos, 'rubrica': prueba.rubrica_log}
    return render(request, 'simce/admin_revisar.html', ctx)


@login_required
@user_passes_test(is_staff)
@require_POST
def admin_aprobar(request, pk):
    prueba = get_object_or_404(Prueba, pk=pk)
    prueba.estado      = 'aprobada'
    prueba.aprobada_por = request.user
    prueba.aprobada_en  = timezone.now()
    prueba.save()
    messages.success(request, f'Prueba aprobada: {prueba.titulo}')
    return redirect('simce:admin_dashboard')


@login_required
@user_passes_test(is_staff)
@require_POST
def admin_publicar(request, pk):
    prueba = get_object_or_404(Prueba, pk=pk)
    prueba.estado = 'publicada'
    prueba.save()
    messages.success(request, f'Prueba publicada. Los estudiantes ya pueden acceder.')
    return redirect('simce:admin_dashboard')


# ── Estudiante: Identificación ────────────────────────────────────

def prueba_identificacion(request, pk):
    prueba = get_object_or_404(Prueba, pk=pk, estado='publicada')

    if request.method == 'POST':
        nombre      = request.POST.get('nombre', '').strip()
        rut         = request.POST.get('rut', '').strip()
        curso       = request.POST.get('curso')
        letra       = request.POST.get('letra')
        estab       = request.POST.get('establecimiento', '').strip()
        rbd         = request.POST.get('rbd', '').strip()

        if not all([nombre, rut, curso, letra, estab]):
            messages.error(request, 'Completa todos los campos obligatorios.')
        else:
            sesion = SesionEstudiante.objects.create(
                prueba=prueba, nombre=nombre, rut=rut,
                curso=curso, letra_curso=letra,
                establecimiento=estab, rbd=rbd,
            )
            return redirect('simce:prueba_rendir', sesion_pk=sesion.pk)

    ctx = {'prueba': prueba, 'cursos': CURSO_CHOICES}
    return render(request, 'simce/prueba_identificacion.html', ctx)


# ── Estudiante: Rendir prueba ─────────────────────────────────────

def prueba_rendir(request, sesion_pk):
    sesion = get_object_or_404(SesionEstudiante, pk=sesion_pk, completada=False)
    prueba = sesion.prueba
    textos = prueba.textos.prefetch_related('preguntas__alternativas').all()

    if request.method == 'POST':
        preguntas = Pregunta.objects.filter(texto__prueba=prueba)
        for pregunta in preguntas:
            letra = request.POST.get(f'p_{pregunta.pk}')
            alternativa = None
            if letra:
                alternativa = pregunta.alternativas.filter(letra=letra).first()
            RespuestaEstudiante.objects.update_or_create(
                sesion=sesion, pregunta=pregunta,
                defaults={'alternativa_elegida': alternativa}
            )
        sesion.calcular_puntajes()
        return redirect('simce:prueba_resultado', sesion_pk=sesion.pk)

    ctx = {'sesion': sesion, 'prueba': prueba, 'textos': textos}
    return render(request, 'simce/prueba_rendir.html', ctx)


# ── Estudiante: Resultado ─────────────────────────────────────────

def prueba_resultado(request, sesion_pk):
    sesion = get_object_or_404(SesionEstudiante, pk=sesion_pk, completada=True)
    respuestas = sesion.respuestas.select_related(
        'pregunta', 'pregunta__texto', 'alternativa_elegida'
    ).order_by('pregunta__orden')
    ctx = {'sesion': sesion, 'respuestas': respuestas}
    return render(request, 'simce/prueba_resultado.html', ctx)


# ── Reportes UTP ──────────────────────────────────────────────────

@login_required
def reportes_dashboard(request):
    # UTP ve su establecimiento; staff ve todo
    pruebas = Prueba.objects.filter(estado__in=['publicada', 'cerrada']).annotate(
        n_sesiones=Count('sesiones', filter=Q(sesiones__completada=True)),
        promedio_logro=Avg('sesiones__porcentaje_logro', filter=Q(sesiones__completada=True)),
        promedio_simce=Avg('sesiones__puntaje_simce', filter=Q(sesiones__completada=True)),
    )

    # Filtros
    asignatura_f = request.GET.get('asignatura', '')
    curso_f      = request.GET.get('curso', '')
    if asignatura_f:
        pruebas = pruebas.filter(asignatura=asignatura_f)
    if curso_f:
        pruebas = pruebas.filter(curso=curso_f)

    ctx = {
        'pruebas': pruebas,
        'asignaturas': ASIGNATURA_CHOICES,
        'cursos': CURSO_CHOICES,
        'filtros': {'asignatura': asignatura_f, 'curso': curso_f},
    }
    return render(request, 'simce/reportes_dashboard.html', ctx)


@login_required
def reporte_prueba(request, pk):
    prueba = get_object_or_404(Prueba, pk=pk)
    sesiones = SesionEstudiante.objects.filter(prueba=prueba, completada=True)

    # Filtros
    estab_f  = request.GET.get('establecimiento', '')
    curso_f  = request.GET.get('curso', '')
    letra_f  = request.GET.get('letra', '')
    if estab_f:  sesiones = sesiones.filter(establecimiento=estab_f)
    if curso_f:  sesiones = sesiones.filter(curso=curso_f)
    if letra_f:  sesiones = sesiones.filter(letra_curso=letra_f)

    # Análisis por pregunta
    preguntas = Pregunta.objects.filter(texto__prueba=prueba).order_by('orden')
    analisis_preguntas = []
    for p in preguntas:
        respuestas_p = RespuestaEstudiante.objects.filter(
            sesion__in=sesiones, pregunta=p
        )
        total = respuestas_p.count()
        correctas = respuestas_p.filter(alternativa_elegida__es_correcta=True).count()
        dist = {l: respuestas_p.filter(alternativa_elegida__letra=l).count() for l in 'ABCD'}
        analisis_preguntas.append({
            'pregunta': p,
            'total': total,
            'correctas': correctas,
            'pct_logro': round(correctas / total * 100, 1) if total else 0,
            'dist': dist,
        })

    establecimientos = sesiones.values_list('establecimiento', flat=True).distinct()

    ctx = {
        'prueba': prueba,
        'sesiones': sesiones,
        'analisis': analisis_preguntas,
        'establecimientos': establecimientos,
        'cursos': CURSO_CHOICES,
        'filtros': {'establecimiento': estab_f, 'curso': curso_f, 'letra': letra_f},
        'promedio_logro': sesiones.aggregate(p=Avg('porcentaje_logro'))['p'] or 0,
        'promedio_simce': sesiones.aggregate(p=Avg('puntaje_simce'))['p'] or 0,
    }
    return render(request, 'simce/reporte_prueba.html', ctx)


@login_required
def reporte_estudiante(request, sesion_pk):
    sesion = get_object_or_404(SesionEstudiante, pk=sesion_pk, completada=True)
    respuestas = sesion.respuestas.select_related(
        'pregunta', 'pregunta__texto',
        'alternativa_elegida', 'pregunta__texto'
    ).prefetch_related('pregunta__alternativas').order_by('pregunta__orden')

    ctx = {'sesion': sesion, 'respuestas': respuestas}
    return render(request, 'simce/reporte_estudiante.html', ctx)
