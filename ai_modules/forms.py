from django import forms
from .models import AIQuery

class AIQueryForm(forms.ModelForm):
    class Meta:
        model = AIQuery
        fields = ['question', 'attachment']
        widgets = {
            'question': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Escribe tu consulta detallada para la IA aquí...',
                'style': 'width: 100%; border-radius: 8px; padding: 12px; border: 1px solid #ccc;'
            })
        }
        labels = {
            'attachment': 'Adjuntar archivo (opcional — PDF, imagen, Word)',
        }
