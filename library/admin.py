from django.contrib import admin
from .models import Category, Document

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'version', 'category', 'establishment', 'author', 'upload_date', 'is_mandatory', 'expiry_alert_date']
    list_filter = ['category', 'establishment', 'is_mandatory', 'cargo_type']
    search_fields = ['title', 'description', 'materia']
    readonly_fields = ['upload_date']
