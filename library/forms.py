from django import forms
from .models import Document, Category


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = [
            'title', 'file', 'category', 'establishment',
            'description', 'version', 'parent_document',
            'cargo_type', 'materia', 'is_mandatory', 'expiry_alert_date',
        ]
        widgets = {
            'expiry_alert_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
