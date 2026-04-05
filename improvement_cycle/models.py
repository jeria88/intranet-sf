from django.db import models
from django.conf import settings
from users.models import User


class ImprovementGoal(models.Model):
    STATUS_CHOICES = [
        ('en_progreso', 'En Progreso'),
        ('cumplido',    'Cumplido'),
        ('en_riesgo',   'En Riesgo'),
        ('vencido',     'Vencido'),
    ]
    SUBVENTION_CHOICES = [
        ('SEP', 'SEP'),
        ('PIE', 'PIE'),
        ('MANTENCION', 'Mantención'),
        ('PRO_RETENCION', 'Pro-Retención'),
        ('OTRO', 'Otro'),
    ]
    establishment = models.CharField(
        max_length=20, choices=User.ESTABLISHMENT_CHOICES, verbose_name='Establecimiento'
    )
    profile_role = models.CharField(
        max_length=20, choices=User.ROLE_CHOICES, blank=True, verbose_name='Rol responsable'
    )
    subvention_type = models.CharField(
        max_length=20, choices=SUBVENTION_CHOICES, default='SEP', verbose_name='Tipo de Subvención'
    )
    title = models.CharField(max_length=200, verbose_name='Meta')
    description = models.TextField(blank=True, verbose_name='Resumen/Descripción')
    target_value = models.FloatField(verbose_name='Valor meta')
    current_value = models.FloatField(default=0, verbose_name='Valor actual')
    measurement_unit = models.CharField(max_length=50, verbose_name='Unidad')  # %, reuniones, docs
    deadline = models.DateField(verbose_name='Plazo')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='en_progreso')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='goals'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['deadline', 'establishment']
        verbose_name = 'Meta de Mejora'
        verbose_name_plural = 'Metas de Mejora'

    @property
    def actions_summary(self):
        total = self.actions.count()
        completed = self.actions.filter(status='completado').count()
        return f"{completed} de {total} acciones"

    @property
    def progress_pct(self):
        """Calcula el progreso basado en las acciones si existen, si no usa current_value."""
        actions = self.actions.all()
        if actions.exists():
            total_weight = sum(a.weight for a in actions)
            if total_weight == 0: return 0
            completed_weight = sum(a.weight for a in actions if a.status == 'completado')
            return round((completed_weight / total_weight) * 100, 1)
        
        if self.target_value == 0: return 0
        return min(100, round((self.current_value / self.target_value) * 100, 1))

    def __str__(self):
        return f"{self.establishment} — {self.title} ({self.progress_pct}%)"


class ImprovementAction(models.Model):
    STATUS_CHOICES = [
        ('pendiente',   'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completado',  'Completado'),
        ('cancelado',   'Cancelado'),
    ]
    goal = models.ForeignKey(ImprovementGoal, on_delete=models.CASCADE, related_name='actions')
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, 
        limit_choices_to={'is_active': True}, verbose_name='Responsable'
    )
    title = models.CharField(max_length=200, verbose_name='Acción/Hito')
    description = models.TextField(blank=True, verbose_name='Descripción de la acción')
    evidence = models.TextField(blank=True, verbose_name='Evidencia / Observaciones')
    deadline = models.DateField(verbose_name='Plazo de la acción')
    weight = models.FloatField(default=1.0, verbose_name='Peso/Importancia (1-100)')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pendiente')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['deadline', 'created_at']
        verbose_name = 'Acción de Mejora'
        verbose_name_plural = 'Acciones de Mejora'

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class RiskAlert(models.Model):
    ALERT_TYPE_CHOICES = [
        ('plazo_mineduc',       'Plazo MINEDUC'),
        ('brecha_normativa',    'Brecha Normativa'),
        ('documento_vencido',   'Documento Vencido'),
        ('meta_en_riesgo',      'Meta en Riesgo'),
        ('consulta_ia_vencida', 'Consulta IA Vencida'),
        ('reunion_cuota',       'Cuota de Reuniones Alcanzada'),
    ]
    alert_type = models.CharField(max_length=25, choices=ALERT_TYPE_CHOICES, verbose_name='Tipo de Alerta')
    description = models.TextField(verbose_name='Descripción')
    affected_establishments = models.JSONField(default=list, verbose_name='Establecimientos afectados')
    triggered_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    # Referencia genérica al objeto que generó la alerta
    related_object_info = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-triggered_at']
        verbose_name = 'Alerta de Riesgo'
        verbose_name_plural = 'Alertas de Riesgo'

    def resolve(self):
        from django.utils import timezone
        self.is_active = False
        self.resolved_at = timezone.now()
        self.save(update_fields=['is_active', 'resolved_at'])

    def __str__(self):
        return f"[{self.get_alert_type_display()}] {self.description[:60]}"
