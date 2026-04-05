from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def mis_notificaciones(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    # Marcar todas como leídas al visitar
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications/mis_notificaciones.html', {'notifications': notifications})
