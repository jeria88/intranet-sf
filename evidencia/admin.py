from django.contrib import admin
from .models import EvaluationForm, EvidenceDocument

@admin.register(EvaluationForm)
class EvaluationFormAdmin(admin.ModelAdmin):
    list_display = ['title', 'session_type', 'applied_at', 'created_by']
    list_filter = ['session_type']

@admin.register(EvidenceDocument)
class EvidenceDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'session_type', 'session_date', 'uploaded_by']
    list_filter = ['category', 'session_type']
