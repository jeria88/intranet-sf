import json
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from .models import (Prueba, TextoPrueba, Pregunta, Alternativa,
                     SesionEstudiante, RespuestaEstudiante,
                     ASIGNATURA_CHOICES, CURSO_CHOICES, TIPO_TEXTUAL_CHOICES)
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


# ── Admin: Generar prueba con IA (async) ─────────────────────────

def _guardar_resultado(prueba, resultado):
    """Persiste textos y preguntas generados. Llamado desde hilo background."""
    from django.db import connection
    try:
        rubrica = resultado['rubrica']
        prueba.titulo     = resultado['titulo']
        prueba.rubrica_ok = rubrica['aprobado']
        prueba.rubrica_log = rubrica
        prueba.estado     = 'revision'
        prueba.save()

        orden_global = 1
        for t_data in resultado['textos']:
            texto = TextoPrueba.objects.create(
                prueba=prueba, orden=t_data['orden'],
                tipo_textual=t_data['tipo_textual'],
                titulo=t_data['titulo'], contenido=t_data['contenido'],
            )
            for p_data in t_data['preguntas']:
                pregunta = Pregunta.objects.create(
                    texto=texto, orden=orden_global,
                    enunciado=p_data['enunciado'], nivel=p_data['nivel'],
                    habilidad=p_data['habilidad'],
                    habilidad_justificacion=p_data.get('habilidad_justificacion', ''),
                    nivel_justificacion=p_data.get('nivel_justificacion', ''),
                    alternativa_correcta=p_data['alternativa_correcta'],
                    pista_1=p_data.get('pista_1', ''),
                    pista_2=p_data.get('pista_2', ''),
                )
                for a_data in p_data['alternativas']:
                    Alternativa.objects.create(
                        pregunta=pregunta, letra=a_data['letra'],
                        texto=a_data['texto'], es_correcta=a_data['es_correcta'],
                        justificacion=a_data.get('justificacion', ''),
                    )
                orden_global += 1
    except Exception as e:
        prueba.titulo     = f'Error: {str(e)[:120]}'
        prueba.estado     = 'error'
        prueba.rubrica_log = {'error': str(e)}
        prueba.save()
    finally:
        connection.close()


def _hilo_generacion(prueba_pk, asignatura, curso, titulo):
    try:
        resultado = generar_prueba_completa(asignatura, curso, titulo)
        prueba = Prueba.objects.get(pk=prueba_pk)
        _guardar_resultado(prueba, resultado)
    except Exception as e:
        try:
            prueba = Prueba.objects.get(pk=prueba_pk)
            prueba.titulo  = f'Error: {str(e)[:120]}'
            prueba.estado  = 'error'
            prueba.rubrica_log = {'error': str(e)}
            prueba.save()
        except Exception:
            pass
        from django.db import connection
        connection.close()


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

    # Crear registro placeholder inmediatamente
    prueba = Prueba.objects.create(
        titulo     = titulo or f'Generando {asignatura.title()} {curso}…',
        asignatura = asignatura,
        curso      = curso,
        estado     = 'generando',
        creada_por = request.user,
    )

    # Lanzar generación en hilo background
    t = threading.Thread(
        target=_hilo_generacion,
        args=(prueba.pk, asignatura, curso, titulo),
        daemon=True,
    )
    t.start()

    return redirect('simce:prueba_generando', pk=prueba.pk)


# ── Admin: Página de espera durante generación ────────────────────

@login_required
@user_passes_test(is_staff)
def prueba_generando(request, pk):
    prueba = get_object_or_404(Prueba, pk=pk)
    return render(request, 'simce/generando.html', {'prueba': prueba})


@login_required
@user_passes_test(is_staff)
def api_estado_prueba(request, pk):
    prueba = get_object_or_404(Prueba, pk=pk)
    return JsonResponse({
        'estado': prueba.estado,
        'titulo': prueba.titulo,
        'error':  prueba.rubrica_log.get('error', '') if isinstance(prueba.rubrica_log, dict) else '',
    })


# ── Admin: Revisar prueba ─────────────────────────────────────────

@login_required
@user_passes_test(is_staff)
def admin_revisar(request, pk):
    prueba = get_object_or_404(Prueba, pk=pk)
    textos = prueba.textos.prefetch_related('preguntas__alternativas').all()
    ctx = {
        'prueba': prueba,
        'textos': textos,
        'rubrica': prueba.rubrica_log,
        'tipos_textuales': TIPO_TEXTUAL_CHOICES,
    }
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

def prueba_identificacion(request, pk, modo='simce'):
    prueba = get_object_or_404(Prueba, pk=pk, estado='publicada')
    if modo not in ('simce', 'pistas'):
        modo = 'simce'

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
                modo=modo,
            )
            return redirect('simce:prueba_rendir', sesion_pk=sesion.pk)

    ctx = {'prueba': prueba, 'cursos': CURSO_CHOICES, 'modo': modo}
    return render(request, 'simce/prueba_identificacion.html', ctx)


# ── Estudiante: Rendir prueba ─────────────────────────────────────

def prueba_rendir(request, sesion_pk):
    sesion = get_object_or_404(SesionEstudiante, pk=sesion_pk, completada=False)
    prueba = sesion.prueba
    textos = prueba.textos.prefetch_related('preguntas__alternativas').all()

    # Preguntas ya respondidas (para restaurar estado en caso de recarga)
    respondidas = {
        r.pregunta_id: {
            'puntaje': r.puntaje_obtenido,
            'intentos': r.intentos,
            'correcta': r.alternativa_elegida.es_correcta if r.alternativa_elegida else False,
            'letra_elegida': r.alternativa_elegida.letra if r.alternativa_elegida else None,
        }
        for r in sesion.respuestas.select_related('alternativa_elegida').all()
    }

    ctx = {
        'sesion': sesion,
        'prueba': prueba,
        'textos': textos,
        'respondidas_json': json.dumps(respondidas),
        'total_preguntas': Pregunta.objects.filter(texto__prueba=prueba).count(),
        'modo': sesion.modo,
    }
    return render(request, 'simce/prueba_rendir.html', ctx)


# ── AJAX: Verificar respuesta individual ─────────────────────────

@require_POST
def verificar_respuesta(request, sesion_pk, pregunta_pk):
    sesion   = get_object_or_404(SesionEstudiante, pk=sesion_pk, completada=False)
    pregunta = get_object_or_404(Pregunta, pk=pregunta_pk, texto__prueba=sesion.prueba)

    # No permitir reverificar una pregunta ya resuelta
    if sesion.respuestas.filter(pregunta=pregunta).exists():
        return JsonResponse({'error': 'ya_respondida'}, status=400)

    letra = request.POST.get('letra', '').upper()
    if letra not in ['A', 'B', 'C', 'D']:
        return JsonResponse({'error': 'letra_invalida'}, status=400)

    # Obtener/inicializar contador de intentos desde sesión Django
    sesion_key = f'simce_{sesion_pk}_{pregunta_pk}_intentos'
    intento_actual = request.session.get(sesion_key, 0) + 1
    request.session[sesion_key] = intento_actual

    alternativa = pregunta.alternativas.filter(letra=letra).first()
    es_correcta = alternativa and alternativa.es_correcta

    # Calcular puntaje según intento
    puntaje_map = {1: 4, 2: 3, 3: 2}

    if es_correcta:
        puntaje = puntaje_map.get(intento_actual, 2)
        RespuestaEstudiante.objects.create(
            sesion=sesion, pregunta=pregunta,
            alternativa_elegida=alternativa,
            intentos=intento_actual,
            puntaje_obtenido=puntaje,
        )
        del request.session[sesion_key]
        return JsonResponse({
            'resultado': 'correcto',
            'puntaje': puntaje,
            'intentos': intento_actual,
        })

    # Respuesta incorrecta
    if intento_actual >= 3:
        # Tercer intento fallido: guardar con puntaje 0
        correcta_alt = pregunta.alternativas.filter(es_correcta=True).first()
        RespuestaEstudiante.objects.create(
            sesion=sesion, pregunta=pregunta,
            alternativa_elegida=alternativa,
            intentos=3,
            puntaje_obtenido=0,
        )
        del request.session[sesion_key]
        return JsonResponse({
            'resultado': 'fallido',
            'puntaje': 0,
            'intentos': 3,
            'letra_correcta': correcta_alt.letra if correcta_alt else pregunta.alternativa_correcta,
        })

    # Todavía hay intentos: devolver pista
    pista = pregunta.pista_1 if intento_actual == 1 else pregunta.pista_2
    return JsonResponse({
        'resultado': 'incorrecto',
        'intento': intento_actual,
        'pista': pista or '💡 Vuelve a leer el texto con atención antes de intentarlo de nuevo.',
        'intentos_restantes': 3 - intento_actual,
    })


# ── Estudiante: Finalizar prueba ──────────────────────────────────

@require_POST
def finalizar_prueba(request, sesion_pk):
    sesion  = get_object_or_404(SesionEstudiante, pk=sesion_pk, completada=False)
    prueba  = sesion.prueba
    preguntas = Pregunta.objects.filter(texto__prueba=prueba)

    # Crear respuesta vacía para preguntas sin contestar (puntaje 0)
    respondidas_ids = set(sesion.respuestas.values_list('pregunta_id', flat=True))
    for p in preguntas:
        if p.pk not in respondidas_ids:
            RespuestaEstudiante.objects.create(
                sesion=sesion, pregunta=p,
                alternativa_elegida=None,
                intentos=0,
                puntaje_obtenido=0,
            )

    sesion.calcular_puntajes()
    return JsonResponse({'redirect': f'/simce/resultado/{sesion.pk}/'}, status=200)


# ── Estudiante: Entregar modo SIMCE (submit tradicional) ─────────

@require_POST
def entregar_simce(request, sesion_pk):
    sesion   = get_object_or_404(SesionEstudiante, pk=sesion_pk, completada=False)
    prueba   = sesion.prueba
    preguntas = Pregunta.objects.filter(texto__prueba=prueba)

    for pregunta in preguntas:
        letra = request.POST.get(f'p_{pregunta.pk}')
        alternativa = pregunta.alternativas.filter(letra=letra).first() if letra else None
        es_correcta = alternativa.es_correcta if alternativa else False
        RespuestaEstudiante.objects.update_or_create(
            sesion=sesion, pregunta=pregunta,
            defaults={
                'alternativa_elegida': alternativa,
                'intentos': 1,
                'puntaje_obtenido': 1 if es_correcta else 0,
            }
        )

    sesion.calcular_puntajes()
    return redirect('simce:prueba_resultado', sesion_pk=sesion.pk)


# ── Estudiante: Resultado ─────────────────────────────────────────

def prueba_resultado(request, sesion_pk):
    sesion = get_object_or_404(SesionEstudiante, pk=sesion_pk, completada=True)
    respuestas = sesion.respuestas.select_related(
        'pregunta', 'pregunta__texto', 'alternativa_elegida'
    ).order_by('pregunta__orden')
    ctx = {'sesion': sesion, 'respuestas': respuestas}
    return render(request, 'simce/prueba_resultado.html', ctx)


# ── CRUD API ──────────────────────────────────────────────────────

@login_required
@user_passes_test(is_staff)
@require_http_methods(['GET', 'POST', 'DELETE'])
def api_texto(request, pk):
    texto = get_object_or_404(TextoPrueba, pk=pk)

    if request.method == 'GET':
        return JsonResponse({
            'pk': texto.pk,
            'titulo': texto.titulo,
            'tipo_textual': texto.tipo_textual,
            'contenido': texto.contenido,
            'char_count': texto.char_count,
        })

    if request.method == 'POST':
        texto.titulo       = request.POST.get('titulo', texto.titulo).strip()
        texto.tipo_textual = request.POST.get('tipo_textual', texto.tipo_textual)
        texto.contenido    = request.POST.get('contenido', texto.contenido).strip()
        texto.save()
        return JsonResponse({
            'ok': True,
            'titulo': texto.titulo,
            'tipo_textual_display': texto.get_tipo_textual_display(),
            'char_count': texto.char_count,
            'cumple': texto.cumple_extension(),
        })

    # DELETE — solo si la prueba está en revisión
    if texto.prueba.estado != 'revision':
        return JsonResponse({'error': 'solo_en_revision'}, status=403)
    prueba_pk = texto.prueba.pk
    texto.delete()
    return JsonResponse({'ok': True, 'redirect': f'/simce/revisar/{prueba_pk}/'})


@login_required
@user_passes_test(is_staff)
@require_http_methods(['GET', 'POST', 'DELETE'])
def api_pregunta(request, pk):
    pregunta = get_object_or_404(Pregunta, pk=pk)

    if request.method == 'GET':
        alts = {a.letra: {'texto': a.texto, 'justificacion': a.justificacion}
                for a in pregunta.alternativas.all()}
        return JsonResponse({
            'pk': pregunta.pk,
            'enunciado': pregunta.enunciado,
            'nivel': pregunta.nivel,
            'habilidad': pregunta.habilidad,
            'alternativa_correcta': pregunta.alternativa_correcta,
            'pista_1': pregunta.pista_1,
            'pista_2': pregunta.pista_2,
            'alternativas': alts,
        })

    if request.method == 'POST':
        pregunta.enunciado            = request.POST.get('enunciado', pregunta.enunciado).strip()
        pregunta.nivel                = int(request.POST.get('nivel', pregunta.nivel))
        pregunta.habilidad            = request.POST.get('habilidad', pregunta.habilidad).strip()
        pregunta.alternativa_correcta = request.POST.get('alternativa_correcta', pregunta.alternativa_correcta)
        pregunta.pista_1              = request.POST.get('pista_1', pregunta.pista_1).strip()
        pregunta.pista_2              = request.POST.get('pista_2', pregunta.pista_2).strip()
        pregunta.save()

        for letra in ['A', 'B', 'C', 'D']:
            texto_alt = request.POST.get(f'alt_{letra}', '').strip()
            if texto_alt:
                alt = pregunta.alternativas.filter(letra=letra).first()
                if alt:
                    alt.texto      = texto_alt
                    alt.es_correcta = (letra == pregunta.alternativa_correcta)
                    alt.save()
        # Sincronizar es_correcta para todas las alternativas
        pregunta.alternativas.exclude(letra=pregunta.alternativa_correcta).update(es_correcta=False)
        pregunta.alternativas.filter(letra=pregunta.alternativa_correcta).update(es_correcta=True)

        return JsonResponse({'ok': True, 'nivel': pregunta.nivel,
                             'nivel_estrellas': pregunta.nivel_estrellas(),
                             'alternativa_correcta': pregunta.alternativa_correcta})

    # DELETE
    if pregunta.texto.prueba.estado != 'revision':
        return JsonResponse({'error': 'solo_en_revision'}, status=403)
    if pregunta.texto.preguntas.count() <= 1:
        return JsonResponse({'error': 'minimo_una_pregunta'}, status=400)
    pregunta.delete()
    return JsonResponse({'ok': True})


@login_required
@user_passes_test(is_staff)
@require_http_methods(['DELETE', 'POST'])
def api_sesion(request, pk):
    sesion = get_object_or_404(SesionEstudiante, pk=pk)
    prueba_pk = sesion.prueba.pk
    sesion.delete()
    return JsonResponse({'ok': True, 'prueba_pk': prueba_pk})


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
