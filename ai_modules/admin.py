from django.contrib import admin
from .models import AIAssistant, AIQuery

@admin.register(AIAssistant)
class AIAssistantAdmin(admin.ModelAdmin):
    list_display = ['name', 'profile_role', 'is_active', 'establishment']
    list_filter = ['profile_role', 'is_active']

@admin.register(AIQuery)
class AIQueryAdmin(admin.ModelAdmin):
    list_display = ['user', 'assistant', 'status', 'submitted_at', 'deadline', 'answered_by']
    list_filter = ['status', 'assistant']
    search_fields = ['question', 'answer', 'user__username']
    readonly_fields = ['submitted_at', 'deadline']
    ordering = ['deadline']
