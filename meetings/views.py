from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
import json
from django.utils import timezone
from django.conf import settings
import requests
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


def _generate_daily_token(room_name, user_name, is_owner=False):
    """
    Solicita un token de acceso a la API de Daily.co.
    """
    api_key = settings.DAILY_API_KEY
    if not api_key:
        return None
    
    url = "https://api.daily.co/v1/meeting-tokens"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "properties": {
            "room_name": room_name,
            "user_name": user_name,
            "is_owner": is_owner
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=5)
        if response.status_code == 200:
            return response.json().get('token')
        else:
            print(f"Daily API Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Daily Connection Error: {e}")
    
    return None


@login_required
def meeting_list(request):
    user = request.user
    now = timezone.now()

    if user.is_staff:
        rooms_est = MeetingRoom.objects.filter(room_type='daily').exclude(target_establishment='')
        rooms_role = MeetingRoom.objects.filter(room_type='daily').exclude(target_role='')
    else:
        rooms_est = MeetingRoom.objects.filter(target_establishment=user.establishment, room_type='daily')
        rooms_role = MeetingRoom.objects.filter(target_role=user.role, room_type='daily')

    def _process_room_status(room):
        # 1. ¿Hay una reunión EN CURSO ahora?
        current = MeetingBooking.objects.filter(
            room=room,
            scheduled_at__lte=now,
            status__in=['programada', 'activa']
        ).order_by('-scheduled_at').first()
        
        if current and now < current.end_time:
            room.status_label = 'EN_CURSO'
            room.active_booking = current
            return

        # 2. ¿Hay una reunión PRÓXIMA hoy?
        next_booking = MeetingBooking.objects.filter(
            room=room,
            scheduled_at__gt=now,
            scheduled_at__date=now.date(),
            status='programada'
        ).order_by('scheduled_at').first()
        
        if next_booking:
            room.status_label = 'PROXIMA'
            room.next_booking = next_booking
        else:
            room.status_label = 'LIBRE'

    # Procesar estados
    for r in rooms_est:
        _process_room_status(r)
    for r in rooms_role:
        _process_room_status(r)

    month_year = now.strftime('%Y-%m')
    user_count = MeetingBooking.objects.filter(booked_by=user, month_year=month_year).exclude(status='cancelada').count()
    quota_remaining = None if user.is_red_team else max(0, MONTHLY_QUOTA - user_count)
    
    return render(request, 'meetings/meeting_list.html', {
        'rooms_est': rooms_est,
        'rooms_role': rooms_role,
        'quota_remaining': quota_remaining,
    })


@login_required
def meeting_room(request, slug):
    room = get_object_or_404(MeetingRoom, slug=slug)
    now = timezone.now()
    
    # 1. Buscar si hay una reserva formal en curso
    booking = MeetingBooking.objects.filter(
        room=room, 
        scheduled_at__lte=now,
        status__in=['programada', 'activa']
    ).order_by('-scheduled_at').first()

    # Si la reserva ya terminó (según duración), no es la "actual"
    if booking and now >= booking.end_time:
        booking = None

    # 2. Si no hay reserva y no es staff, validamos si la sala está libre para entrada ad-hoc
    if not booking:
        # Verificar si hay alguna reserva que empiece MUY pronto (margen de 5 min)
        conflict = MeetingBooking.objects.filter(
            room=room,
            scheduled_at__range=(now, now + timezone.timedelta(minutes=5)),
            status='programada'
        ).exists()
        
        if conflict and not request.user.is_staff:
            messages.warning(request, "La sala estará ocupada en breve por una reunión agendada.")
            return redirect('meetings:meeting_list')
        
        # Entrada Libre: Creamos una reserva "al vuelo" para auditoría y acuerdos
        if not request.user.is_staff:
            if not _check_quota(request.user, room):
                messages.error(request, "No tienes cupo para iniciar una reunión ahora.")
                return redirect('meetings:meeting_list')
            
            booking = MeetingBooking.objects.create(
                room=room,
                booked_by=request.user,
                scheduled_at=now,
                duration_minutes=60,
                status='activa',
                agenda='Reunión espontánea (Sin agenda previa)'
            )

    # Redirección a Daily.co
    if room.room_type == 'daily':
        daily_url = f"{settings.DAILY_BASE_URL}{room.daily_identifier}"
        token = _generate_daily_token(
            room.daily_identifier, 
            request.user.get_full_name() or request.user.username,
            is_owner=(request.user.is_staff or (booking and booking.booked_by == request.user))
        )
        if token:
            daily_url = f"{daily_url}?t={token}"
        if booking:
            MeetingAttendance.objects.get_or_create(booking=booking, user=request.user)
        return redirect(daily_url)

    # Jitsi fallback
    if booking:
        MeetingAttendance.objects.get_or_create(booking=booking, user=request.user)
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
                
                # Sincronización con Calendario
                from calendar_red.models import CalendarEvent
                event = CalendarEvent.objects.create(
                    title=f"Videollamada: {room.name}",
                    description=f"Agenda: {agenda}",
                    event_date=scheduled_at.date(),
                    event_time=scheduled_at.time(),
                    event_type='interno',
                    applies_to_roles=[request.user.role],
                    applies_to_establishments=[request.user.establishment],
                    created_by=request.user,
                )

                MeetingBooking.objects.create(
                    room=room, booked_by=request.user,
                    scheduled_at=scheduled_at, agenda=agenda,
                    calendar_event=event
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
    Repositorio de grabaciones. Filtrado por perfil de usuario.
    """
    # 1. Base del QuerySet: solo aquello que tiene video
    bookings = MeetingBooking.objects.filter(
        Q(recording_url__isnull=False)
    ).exclude(recording_url='')

    # 2. Filtro de SEGURIDAD (Segmentación por Perfil)
    if not request.user.is_red_team and not request.user.is_staff:
        # El usuario solo ve videos de: Su establecimiento O Su Rol
        bookings = bookings.filter(
            Q(room__target_establishment=request.user.establishment) |
            Q(room__target_role=request.user.role)
        )

    # 3. Filtros Manuales de Búsqueda (GET params)
    est = request.GET.get('establishment')
    role = request.GET.get('role')
    month = request.GET.get('month')
    
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


@csrf_exempt
def recording_webhook(request):
    """
    Recibe notificaciones de Daily.co cuando una grabación está lista.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    try:
        data = json.loads(request.body)
        event_type = data.get('type')
        payload = data.get('payload', {})
        
        if event_type == 'recording.ready-to-download':
            room_id = payload.get('room_name')
            download_url = payload.get('download_url')
            
            if room_id and download_url:
                # Buscar la sala por su identificador de Daily
                room = MeetingRoom.objects.filter(daily_identifier=room_id).first()
                if room:
                    # Vincular a la reserva más reciente (activa o recientemente programada)
                    booking = MeetingBooking.objects.filter(room=room).order_by('-scheduled_at').first()
                    if booking:
                        booking.recording_url = download_url
                        booking.save(update_fields=['recording_url'])
                        print(f"✅ Grabación vinculada a reserva: {booking}")
        
        return JsonResponse({"status": "received"})
    except Exception as e:
        print(f"Webhook Error: {e}")
        return HttpResponse(status=400)


@login_required
def sync_daily_recordings(request):
    """
    Sincroniza manualmente las grabaciones desde la API de Daily.co.
    Adaptado para obtener enlaces al Dashboard en planes gratuitos.
    """
    if not request.user.is_staff and not request.user.is_red_team:
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect('meetings:recording_list')

    api_key = settings.DAILY_API_KEY
    if not api_key:
        messages.error(request, "Error de configuración: DAILY_API_KEY no encontrada.")
        return redirect('meetings:recording_list')

    url = "https://api.daily.co/v1/recordings"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            messages.error(request, f"Error API Daily: {response.status_code} - {response.text}")
            return redirect('meetings:recording_list')
        
        data = response.json()
        recordings = data.get('data', [])
        total_found = len(recordings)
        synced_count = 0
        matches_room_but_not_time = 0

        for rec in recordings:
            recording_id = rec.get('id')
            room_name = (rec.get('room_name') or "").lower().strip()
            # Priorizamos download_url para descarga directa, fallback al dashboard
            download_link = rec.get('download_url') or f"https://dashboard.daily.co/recordings/{recording_id}"
            
            if room_name and recording_id:
                # Buscar sala vinculada
                room = MeetingRoom.objects.filter(daily_identifier__iexact=room_name).first()
                if room:
                    # Buscamos la reserva MÁS RECIENTE de esta sala que NO tenga video aún
                    booking = MeetingBooking.objects.filter(
                        Q(recording_url__isnull=True) | Q(recording_url=''),
                        room=room
                    ).order_by('-scheduled_at').first()
                    
                    if booking:
                        booking.recording_url = download_link
                        booking.save(update_fields=['recording_url'])
                        synced_count += 1
                    else:
                        matches_room_but_not_time += 1
        
        if synced_count > 0:
            messages.success(request, f"✅ Sincronización exitosa: {synced_count} grabaciones nuevas vinculadas.")
        elif matches_room_but_not_time > 0:
            messages.warning(request, f"ℹ️ Se encontraron {matches_room_but_not_time} grabaciones en la sala correcta, pero fuera del rango de tiempo.")
        elif total_found > 0:
            messages.info(request, f"🔎 Se encontraron {total_found} grabaciones en Daily.co, pero no coinciden con las salas de la intranet.")
        else:
            messages.info(request, "📭 No se encontraron grabaciones nuevas.")

    except Exception as e:
        messages.error(request, f"❌ Error: {str(e)}")
    
    return redirect('meetings:recording_list')
