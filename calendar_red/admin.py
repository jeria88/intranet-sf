from django.contrib import admin
from .models import CalendarEvent

@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_date', 'event_type', 'is_critical', 'created_by']
    list_filter = ['event_type', 'is_critical']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']
