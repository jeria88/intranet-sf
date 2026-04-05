from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Message
from users.models import User


@login_required
def bandeja_entrada(request):
    messages_in = Message.objects.filter(
        recipient=request.user, is_deleted_by_recipient=False
    ).select_related('sender')
    unread_count = messages_in.filter(is_read=False).count()
    return render(request, 'messaging/bandeja_entrada.html', {
        'messages_in': messages_in,
        'unread_count': unread_count,
    })


@login_required
def bandeja_enviados(request):
    messages_out = Message.objects.filter(
        sender=request.user, is_deleted_by_sender=False
    ).select_related('recipient')
    return render(request, 'messaging/bandeja_enviados.html', {'messages_out': messages_out})


@login_required
def mensaje_nuevo(request):
    recipient_id = request.GET.get('to')
    initial_recipient = None
    if recipient_id:
        try:
            initial_recipient = User.objects.get(pk=recipient_id)
        except User.DoesNotExist:
            pass

    if request.method == 'POST':
        recipient_id = request.POST.get('recipient')
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        if recipient_id and subject and body:
            try:
                recipient = User.objects.get(pk=recipient_id)
                msg = Message.objects.create(
                    sender=request.user, recipient=recipient,
                    subject=subject, body=body,
                )
                # Notificar al destinatario
                from notifications.models import Notification
                Notification.notify(
                    recipient=recipient,
                    notification_type='mensaje',
                    title=f'Nuevo mensaje de {request.user.get_full_name() or request.user.username}',
                    message=subject,
                    url=f'/mensajes/{msg.pk}/',
                )
                return redirect('messaging:bandeja_entrada')
            except User.DoesNotExist:
                pass

    users = User.objects.exclude(pk=request.user.pk).order_by('last_name', 'first_name')
    return render(request, 'messaging/mensaje_nuevo.html', {
        'users': users,
        'initial_recipient': initial_recipient,
    })


@login_required
def mensaje_detalle(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    # Solo remitente o destinatario pueden ver el mensaje
    if msg.sender != request.user and msg.recipient != request.user:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    if msg.recipient == request.user:
        msg.mark_as_read()
    return render(request, 'messaging/mensaje_detalle.html', {'msg': msg})


@login_required
def mensaje_responder(request, pk):
    original = get_object_or_404(Message, pk=pk)
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if body:
            recipient = original.sender if original.recipient == request.user else original.recipient
            Message.objects.create(
                sender=request.user, recipient=recipient,
                subject=f'Re: {original.subject}',
                body=body, parent=original,
            )
        return redirect('messaging:mensaje_detalle', pk=pk)
    return render(request, 'messaging/mensaje_responder.html', {'original': original})
