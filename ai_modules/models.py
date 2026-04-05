from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class AIAssistant(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    profile_role = models.CharField(max_length=20, verbose_name='Rol objetivo')
    notebook_url = models.URLField(verbose_name='URL NotebookLM')
    description = models.TextField(blank=True)
    use_cases = models.TextField(blank=True, verbose_name='Casos de uso (uno por línea)')
    image_name = models.CharField(max_length=100, verbose_name='Nombre de imagen')
    establishment = models.CharField(max_length=20, blank=True, verbose_name='Establecimiento (opcional)')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.profile_role})"

    def get_use_cases_list(self):
        return [u.strip() for u in self.use_cases.splitlines() if u.strip()]


class AIQuery(models.Model):
    STATUS_CHOICES = [
        ('pendiente',   'Pendiente'),
        ('en_proceso',  'En Proceso'),
        ('respondida',  'Respondida'),
        ('vencida',     'Vencida'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_queries'
    )
    assistant = models.ForeignKey(
        AIAssistant, on_delete=models.CASCADE, related_name='queries'
    )
    question = models.TextField(verbose_name='Consulta')
    attachment = models.FileField(upload_to='ai_queries/', blank=True, null=True, verbose_name='Archivo adjunto')
    submitted_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(verbose_name='Plazo de respuesta (24h)', editable=False)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pendiente')
    # Respuesta del admin
    answer = models.TextField(blank=True, verbose_name='Respuesta')
    answered_at = models.DateTimeField(null=True, blank=True)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ai_answers'
    )

    class Meta:
        ordering = ['deadline']
        verbose_name = 'Consulta IA'
        verbose_name_plural = 'Consultas IA'

    def save(self, *args, **kwargs):
        if not self.pk:
            # Calcular deadline al crear (usar submitted_at o timezone.now())
            base_time = self.submitted_at or timezone.now()
            sla_hours = getattr(settings, 'AI_QUERY_SLA_HOURS', 24)
            self.deadline = base_time + timedelta(hours=sla_hours)
        super().save(*args, **kwargs)

    @property
    def is_overdue(self):
        return timezone.now() > self.deadline and self.status not in ('respondida',)

    @property
    def hours_remaining(self):
        delta = self.deadline - timezone.now()
        return max(0, delta.total_seconds() / 3600)

    def __str__(self):
        return f"[{self.get_status_display()}] {self.user} → {self.assistant.name}"
