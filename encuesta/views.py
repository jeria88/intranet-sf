from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from .models import EncuestaSemana


@login_required
def responder(request):
    today = date.today()
    iso = today.isocalendar()
    iso_year, iso_week = iso[0], iso[1]

    # Si ya respondió esta semana, redirigir al portal
    ya_respondio = EncuestaSemana.objects.filter(
        user=request.user, iso_year=iso_year, iso_week=iso_week
    ).exists()

    if ya_respondio:
        return redirect('portal:index')

    error = None

    if request.method == 'POST':
        try:
            p1_score = int(request.POST.get('p1_score', 0))
            p2_score = int(request.POST.get('p2_score', 0))
            p3_score = int(request.POST.get('p3_score', 0))
            p4_score = int(request.POST.get('p4_score', 0))
            p5_score = int(request.POST.get('p5_score', 0))
        except (ValueError, TypeError):
            error = "Por favor, selecciona una opción en cada pregunta."
        else:
            if not all(1 <= s <= 5 for s in [p1_score, p2_score, p3_score, p4_score, p5_score]):
                error = "Todas las preguntas son obligatorias. Por favor selecciona una puntuación del 1 al 5."
            else:
                p1_comentario = request.POST.get('p1_comentario', '').strip()
                p2_comentario = request.POST.get('p2_comentario', '').strip()
                p3_comentario = request.POST.get('p3_comentario', '').strip()
                p4_comentario = request.POST.get('p4_comentario', '').strip()
                p5_comentario = request.POST.get('p5_comentario', '').strip()

                EncuestaSemana.objects.create(
                    user=request.user,
                    iso_year=iso_year,
                    iso_week=iso_week,
                    p1_score=p1_score,
                    p1_comentario=p1_comentario,
                    p2_score=p2_score,
                    p2_comentario=p2_comentario,
                    p3_score=p3_score,
                    p3_comentario=p3_comentario,
                    p4_score=p4_score,
                    p4_comentario=p4_comentario,
                    p5_score=p5_score,
                    p5_comentario=p5_comentario,
                )
                return redirect('encuesta:gracias')

    return render(request, 'encuesta/responder.html', {
        'iso_year': iso_year,
        'iso_week': iso_week,
        'error': error,
    })


@login_required
def gracias(request):
    today = date.today()
    iso = today.isocalendar()
    iso_year, iso_week = iso[0], iso[1]

    encuesta = EncuestaSemana.objects.filter(
        user=request.user, iso_year=iso_year, iso_week=iso_week
    ).first()

    return render(request, 'encuesta/gracias.html', {'encuesta': encuesta})


@login_required
def resultados(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return HttpResponseForbidden("No tienes permiso para ver esta página.")

    encuestas = EncuestaSemana.objects.select_related('user').all()

    encuestas_data = []
    for e in encuestas:
        encuestas_data.append({
            'encuesta': e,
            'promedio': e.promedio(),
        })

    return render(request, 'encuesta/resultados.html', {'encuestas_data': encuestas_data})
