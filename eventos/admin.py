from django.contrib import admin
from .models import EventoCultural


@admin.register(EventoCultural)
class EventoCulturalAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'tipo', 'fecha', 'hora', 'lugar', 'status', 'created_by']
    list_filter = ['tipo', 'status', 'fecha']
    search_fields = ['titulo', 'descripcion', 'lugar']
    readonly_fields = ['created_at', 'updated_at', 'calendar_event']
    date_hierarchy = 'fecha'
