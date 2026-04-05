from notifications.models import Notification


def unread_notifications(request):
    """Inyecta el conteo de notificaciones no leídas en todos los templates."""
    if request.user.is_authenticated:
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}
