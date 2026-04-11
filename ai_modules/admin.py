from django.contrib import admin
from .models import AIAssistant, AIQuery, AIKnowledgeBase
from .utils import process_knowledge_base_file

class AIKnowledgeBaseInline(admin.TabularInline):
    model = AIKnowledgeBase
    extra = 1
    fields = ['name', 'file', 'is_processed']
    readonly_fields = ['is_processed']

@admin.register(AIAssistant)
class AIAssistantAdmin(admin.ModelAdmin):
    list_display = ['name', 'profile_role', 'is_active', 'establishment']
    list_filter = ['profile_role', 'is_active']
    inlines = [AIKnowledgeBaseInline]
    fieldsets = (
        (None, {
            'fields': ('slug', 'name', 'profile_role', 'establishment', 'is_active')
        }),
        ('Contenido IA', {
            'fields': ('system_instruction', 'context_text', 'notebook_url', 'description', 'use_cases', 'image_name'),
            'description': 'Configure las instrucciones y revise el contexto acumulado de los PDFs.'
        }),
    )
    readonly_fields = ['context_text']

@admin.register(AIKnowledgeBase)
class AIKnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ['name', 'assistant', 'is_processed', 'created_at']
    actions = ['process_files']

    def process_files(self, request, queryset):
        for obj in queryset:
            process_knowledge_base_file(obj)
        self.message_user(request, f"Se han procesado {queryset.count()} archivos.")
    process_files.short_description = "Procesar PDFs (Extraer texto)"

@admin.register(AIQuery)
class AIQueryAdmin(admin.ModelAdmin):
    list_display = ['user', 'assistant', 'status', 'submitted_at', 'deadline', 'answered_by']
    list_filter = ['status', 'assistant']
    search_fields = ['question', 'answer', 'user__username']
    readonly_fields = ['submitted_at', 'deadline']
    ordering = ['deadline']
