from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import EvaluationForm, EvidenceDocument


@login_required
def formularios(request):
    forms = EvaluationForm.objects.all().order_by('-applied_at')
    return render(request, 'evidencia/formularios.html', {'forms': forms})


@login_required
def reuniones(request):
    presencial_docs = EvidenceDocument.objects.filter(session_type='presencial').order_by('-session_date')
    virtual_docs = EvidenceDocument.objects.filter(session_type='virtual').order_by('-session_date')
    return render(request, 'evidencia/reuniones.html', {
        'presencial_docs': presencial_docs,
        'virtual_docs': virtual_docs,
    })


@login_required
def reunion_presencial(request):
    docs = EvidenceDocument.objects.filter(session_type='presencial').order_by('-session_date')
    return render(request, 'evidencia/reunion_presencial.html', {'docs': docs})


@login_required
def reunion_virtual(request):
    docs = EvidenceDocument.objects.filter(session_type='virtual').order_by('-session_date')
    return render(request, 'evidencia/reunion_virtual.html', {'docs': docs})
