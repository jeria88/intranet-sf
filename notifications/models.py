from django.db import models
from django.conf import settings


class Notification(models.Model):
    """Notificación interna para un usuario (nueva circular, respuesta IA, etc.)"""
    TYPE_CHOICES = [
        ('circular',       'Nueva Circular'),
        ('mensaje',        'Nuevo Mensaje'),
        ('ai_respuesta',   'Respuesta IA Lista'),
        ('ai_vencida',     'Consulta IA Vencida'),
        ('reunion',        'Recordatorio de Reunión'),
        ('alerta',         'Alerta de Riesgo'),
        ('documento',      'Nuevo Documento'),
    ]
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    url = models.CharField(max_length=300, blank=True, verbose_name='URL de destino')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.recipient}: {self.title}"

    @classmethod
    def notify(cls, recipient, notification_type, title, message, url=''):
        """Shortcut para crear notificaciones desde cualquier app."""
        return cls.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            url=url,
        )
