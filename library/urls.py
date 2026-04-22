from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    path('', views.document_list, name='document_list'),
    path('subir/', views.document_upload, name='document_upload'),
    path('<int:pk>/', views.document_detalle, name='document_detalle'),
    path('<int:pk>/editar/', views.document_edit, name='document_edit'),
    path('<int:pk>/eliminar/', views.document_delete, name='document_delete'),
]
