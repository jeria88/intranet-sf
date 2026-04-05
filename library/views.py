from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Document, Category
from users.models import User


@login_required
def document_list(request):
    docs = Document.objects.select_related('category', 'author').all()
    categories = Category.objects.all()
    # Filtros
    q = request.GET.get('q', '')
    cat = request.GET.get('category')
    ee = request.GET.get('establishment')
    cargo = request.GET.get('cargo')
    if q:
        docs = docs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(materia__icontains=q))
    if cat:
        docs = docs.filter(category__id=cat)
    if ee:
        docs = docs.filter(establishment=ee)
    if cargo:
        docs = docs.filter(cargo_type=cargo)
    # Solo mostrar versión más reciente (sin parent_document = raíz)
    # o con parent_document para ver historial completo
    show_all = request.GET.get('show_all')
    if not show_all:
        docs = docs.filter(parent_document__isnull=True)

    return render(request, 'library/document_list.html', {
        'docs': docs,
        'categories': categories,
        'establishments': User.ESTABLISHMENT_CHOICES,
        'roles': User.ROLE_CHOICES,
        'q': q, 'selected_cat': cat, 'selected_ee': ee, 'selected_cargo': cargo,
    })


@login_required
def document_upload(request):
    if request.method == 'POST':
        from .forms import DocumentForm
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.author = request.user
            doc.save()
            return redirect('library:document_list')
    else:
        from .forms import DocumentForm
        form = DocumentForm()
    return render(request, 'library/document_upload.html', {'form': form})


@login_required
def document_detalle(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    versions = Document.objects.filter(
        Q(pk=doc.pk) | Q(parent_document=doc) | Q(parent_document=doc.parent_document, parent_document__isnull=False)
    ).order_by('version')
    return render(request, 'library/document_detalle.html', {'doc': doc, 'versions': versions})
