import calendar
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import EventoCultural


def _can_manage(user):
    return user.is_staff or user.role == 'RED'


def _sync_to_calendar(evento):
    from calendar_red.models import CalendarEvent
    desc = f"{evento.descripcion}\n\nLugar: {evento.lugar}"
    if evento.status == 'publicado':
        if evento.calendar_event:
            ev = evento.calendar_event
            ev.title = evento.titulo
            ev.description = desc
            ev.event_date = evento.fecha
            ev.event_time = evento.hora
            ev.event_type = evento.tipo
            ev.is_active = True
            ev.save()
        else:
            ev = CalendarEvent.objects.create(
                title=evento.titulo,
                description=desc,
                event_date=evento.fecha,
                event_time=evento.hora,
                event_type=evento.tipo,
                applies_to_roles=[],
                applies_to_establishments=[],
                created_by=evento.created_by,
            )
            evento.calendar_event = ev
            evento.save(update_fields=['calendar_event'])
    elif evento.calendar_event:
        evento.calendar_event.is_active = False
        evento.calendar_event.save(update_fields=['is_active'])


@login_required
def evento_list(request):
    if not _can_manage(request.user):
        messages.error(request, "No tienes permiso para acceder a este módulo.")
        return redirect('portal:index')
    eventos = EventoCultural.objects.all()
    return render(request, 'eventos/evento_list.html', {'eventos': eventos})


@login_required
def evento_crear(request):
    if not _can_manage(request.user):
        messages.error(request, "No tienes permiso para crear eventos.")
        return redirect('portal:index')

    if request.method == 'POST':
        titulo = request.POST.get('titulo', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        tipo = request.POST.get('tipo', 'cultural')
        fecha = request.POST.get('fecha')
        hora = request.POST.get('hora') or None
        lugar = request.POST.get('lugar', '').strip()
        status = request.POST.get('status', 'borrador')
        imagen = request.FILES.get('imagen')

        if titulo and descripcion and fecha and lugar:
            evento = EventoCultural.objects.create(
                titulo=titulo, descripcion=descripcion, tipo=tipo,
                fecha=fecha, hora=hora, lugar=lugar, status=status,
                imagen=imagen, created_by=request.user,
            )
            _sync_to_calendar(evento)
            messages.success(request, "Evento creado correctamente.")
            return redirect('eventos:evento_list')
        messages.error(request, "Completa todos los campos obligatorios.")

    return render(request, 'eventos/evento_form.html', {'action': 'Crear'})


@login_required
def evento_editar(request, pk):
    if not _can_manage(request.user):
        messages.error(request, "No tienes permiso para editar eventos.")
        return redirect('portal:index')

    evento = get_object_or_404(EventoCultural, pk=pk)

    if request.method == 'POST':
        evento.titulo = request.POST.get('titulo', '').strip()
        evento.descripcion = request.POST.get('descripcion', '').strip()
        evento.tipo = request.POST.get('tipo', 'cultural')
        evento.fecha = request.POST.get('fecha')
        evento.hora = request.POST.get('hora') or None
        evento.lugar = request.POST.get('lugar', '').strip()
        evento.status = request.POST.get('status', 'borrador')
        if request.FILES.get('imagen'):
            evento.imagen = request.FILES['imagen']
        evento.save()
        _sync_to_calendar(evento)
        messages.success(request, "Evento actualizado correctamente.")
        return redirect('eventos:evento_list')

    return render(request, 'eventos/evento_form.html', {'evento': evento, 'action': 'Editar'})


@login_required
def evento_detalle(request, pk):
    if _can_manage(request.user):
        evento = get_object_or_404(EventoCultural, pk=pk)
    else:
        evento = get_object_or_404(EventoCultural, pk=pk, status__in=['publicado', 'finalizado'])
    return render(request, 'eventos/evento_detalle.html', {'evento': evento, 'can_manage': _can_manage(request.user)})


@login_required
def evento_eliminar(request, pk):
    if not _can_manage(request.user):
        messages.error(request, "No tienes permiso para eliminar eventos.")
        return redirect('portal:index')

    evento = get_object_or_404(EventoCultural, pk=pk)
    if request.method == 'POST':
        if evento.calendar_event:
            evento.calendar_event.is_active = False
            evento.calendar_event.save(update_fields=['is_active'])
        evento.delete()
        messages.success(request, "Evento eliminado correctamente.")
        return redirect('eventos:evento_list')
    return render(request, 'eventos/evento_confirm_delete.html', {'evento': evento})


@login_required
def calendario_eventos(request):
    today = date.today()
    try:
        month_int = int(request.GET.get('m', today.month))
        year_int = int(request.GET.get('y', today.year))
    except ValueError:
        month_int, year_int = today.month, today.year

    can_manage = _can_manage(request.user)
    qs = EventoCultural.objects.all() if can_manage else EventoCultural.objects.filter(status='publicado')

    filter_tipo = request.GET.get('tipo', '')
    if filter_tipo:
        qs = qs.filter(tipo=filter_tipo)

    grid_eventos = list(qs.filter(fecha__month=month_int, fecha__year=year_int))
    upcoming = list(
        (EventoCultural.objects.all() if can_manage else EventoCultural.objects.filter(status='publicado'))
        .filter(fecha__gte=today).order_by('fecha')[:6]
    )

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdays2calendar(year_int, month_int)

    prev_month = month_int - 1 if month_int > 1 else 12
    prev_year = year_int if month_int > 1 else year_int - 1
    next_month = month_int + 1 if month_int < 12 else 1
    next_year = year_int if month_int < 12 else year_int + 1

    return render(request, 'eventos/calendario_eventos.html', {
        'month_days': month_days,
        'current_month': month_int,
        'current_year': year_int,
        'month_name': calendar.month_name[month_int].capitalize(),
        'grid_eventos': grid_eventos,
        'upcoming': upcoming,
        'today': today,
        'can_manage': can_manage,
        'filter_tipo': filter_tipo,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
    })
