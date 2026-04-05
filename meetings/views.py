from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count
from .models import MeetingRoom, MeetingBooking, MeetingAttendance, MeetingDocument, MeetingAgreement

MONTHLY_QUOTA = 4  # Reuniones máximas por usuario por mes (salvo RED)


def _check_quota(user, room):
    """Retorna True si el usuario puede reservar (dentro del cupo)."""
    if user.is_red_team or room.is_unlimited:
        return True
    month_year = timezone.now().strftime('%Y-%m')
    count = MeetingBooking.objects.filter(
        booked_by=user, month_year=month_year
    ).exclude(status='cancelada').count()
    return count < MONTHLY_QUOTA


@login_required
def meeting_list(request):
    rooms = MeetingRoom.objects.all()
    month_year = timezone.now().strftime('%Y-%m')
    user_count = MeetingBooking.objects.filter(
        booked_by=request.user, month_year=month_year
    ).exclude(status='cancelada').count()
    quota_remaining = None if request.user.is_red_team else max(0, MONTHLY_QUOTA - user_count)
    return render(request, 'meetings/meeting_list.html', {
        'rooms': rooms,
        'quota_remaining': quota_remaining,
    })


@login_required
def meeting_room(request, slug):
    room = get_object_or_404(MeetingRoom, slug=slug)
    # Registrar asistencia automáticamente si hay una reserva activa/programada
    booking = MeetingBooking.objects.filter(room=room, status__in=['programada', 'activa']).first()
    if booking:
        MeetingAttendance.objects.get_or_create(booking=booking, user=request.user)
        if booking.status == 'programada':
            booking.status = 'activa'
            booking.save(update_fields=['status'])
    return render(request, 'meetings/meeting_room.html', {'room': room, 'booking': booking})


@login_required
def booking_crear(request, slug):
    room = get_object_or_404(MeetingRoom, slug=slug)
    error = None

    if request.method == 'POST':
        if not _check_quota(request.user, room):
            error = f'Has alcanzado el límite de {MONTHLY_QUOTA} reuniones para este mes.'
        else:
            from datetime import datetime
            scheduled_str = request.POST.get('scheduled_at')
            agenda = request.POST.get('agenda', '')
            try:
                scheduled_at = datetime.fromisoformat(scheduled_str)
                scheduled_at = timezone.make_aware(scheduled_at)
                MeetingBooking.objects.create(
                    room=room, booked_by=request.user,
                    scheduled_at=scheduled_at, agenda=agenda,
                )
                return redirect('meetings:meeting_list')
            except (ValueError, TypeError):
                error = 'Fecha y hora inválidas.'

    return render(request, 'meetings/booking_form.html', {'room': room, 'error': error})


@login_required
def booking_detalle(request, pk):
    booking = get_object_or_404(MeetingBooking, pk=pk)
    agreements = booking.agreements.all()
    documents = booking.documents.all()
    attendances = booking.attendances.select_related('user')

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'agreement':
            desc = request.POST.get('description', '').strip()
            deadline = request.POST.get('deadline') or None
            if desc:
                MeetingAgreement.objects.create(
                    booking=booking, description=desc,
                    responsible=request.user, deadline=deadline,
                )
        elif form_type == 'document':
            title = request.POST.get('title', '').strip()
            f = request.FILES.get('file')
            if title and f:
                MeetingDocument.objects.create(
                    booking=booking, title=title,
                    file=f, uploaded_by=request.user,
                )
    return render(request, 'meetings/booking_detalle.html', {
        'booking': booking,
        'agreements': agreements,
        'documents': documents,
        'attendances': attendances,
    })


@login_required
def start_recording(request, pk):
    """
    Simula el inicio/fin de grabación en Jitsi.
    En un entorno real se comunicaría con la API de Jitsi (Jibri).
    Aquí solo marcaremos la reserva con una URL de video simulada.
    """
    booking = get_object_or_404(MeetingBooking, pk=pk)
    if request.method == 'POST':
        # Simular URL de grabación guardada
        booking.recording_url = f"https://sfared.cl/recordings/jitsi_{booking.slug}_{booking.pk}.mp4"
        booking.save(update_fields=['recording_url'])
    return redirect('meetings:meeting_room', slug=booking.room.slug)


@login_required
def recording_list(request):
    """
    Lista las reuniones grabadas con filtros por establecimiento, rol y mes.
    """
    bookings = MeetingBooking.objects.filter(recording_url__isnull=False).exclude(recording_url='')
    
    # 1. Filtro de permisos (Python-side for SQLite compatibility)
    if not request.user.is_red_team:
        all_rooms = MeetingRoom.objects.all()
        allowed_room_ids = [r.id for r in all_rooms if request.user.role in r.allowed_roles or not r.allowed_roles]
        bookings = bookings.filter(room_id__in=allowed_room_ids)

    # 2. Filtros de búsqueda (GET params)
    est = request.GET.get('establishment')
    role = request.GET.get('role')
    month = request.GET.get('month') # Formato 'MM'

    if est:
        bookings = bookings.filter(booked_by__establishment=est)
    if role:
        bookings = bookings.filter(booked_by__role=role)
    if month:
        bookings = bookings.filter(scheduled_at__month=month)
        
    return render(request, 'meetings/recording_list.html', {
        'bookings': bookings,
        'establishments': request.user.ESTABLISHMENT_CHOICES,
        'roles': request.user.ROLE_CHOICES,
    })
