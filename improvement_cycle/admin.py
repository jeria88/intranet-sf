from django.contrib import admin
from .models import ImprovementGoal, RiskAlert

@admin.register(ImprovementGoal)
class ImprovementGoalAdmin(admin.ModelAdmin):
    list_display = ['title', 'establishment', 'profile_role', 'current_value', 'target_value', 'deadline', 'status']
    list_filter = ['status', 'establishment', 'profile_role']
    readonly_fields = ['created_at']

@admin.register(RiskAlert)
class RiskAlertAdmin(admin.ModelAdmin):
    list_display = ['alert_type', 'description', 'triggered_at', 'is_active', 'resolved_at']
    list_filter = ['alert_type', 'is_active']
    readonly_fields = ['triggered_at']
    actions = ['resolve_alerts']

    @admin.action(description='Marcar seleccionadas como resueltas')
    def resolve_alerts(self, request, queryset):
        for alert in queryset:
            alert.resolve()
