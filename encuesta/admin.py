from django.contrib import admin
from .models import EncuestaSemana


@admin.register(EncuestaSemana)
class EncuestaSemanaAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'get_establecimiento', 'iso_year', 'iso_week',
        'p1_score', 'p2_score', 'p3_score', 'p4_score', 'p5_score',
        'get_promedio', 'respondida_en',
    ]
    list_filter = ['iso_year', 'iso_week']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__establishment']
    readonly_fields = ['respondida_en']
    ordering = ['-iso_year', '-iso_week']

    @admin.display(description='Establecimiento')
    def get_establecimiento(self, obj):
        return obj.user.establishment

    @admin.display(description='Promedio')
    def get_promedio(self, obj):
        return obj.promedio()
