from django import forms
from .models import Document, Category


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = [
            'title', 'file', 'category',
            'description', 'parent_document',
            'cargo_type', 'materia', 'is_mandatory', 'expiry_alert_date',
        ]
        widgets = {
            'expiry_alert_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
