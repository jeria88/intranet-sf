from django.urls import path
from . import views

app_name = 'eventos'

urlpatterns = [
    path('', views.evento_list, name='evento_list'),
    path('crear/', views.evento_crear, name='evento_crear'),
    path('calendario/', views.calendario_eventos, name='calendario_eventos'),
    path('<int:pk>/', views.evento_detalle, name='evento_detalle'),
    path('<int:pk>/editar/', views.evento_editar, name='evento_editar'),
    path('<int:pk>/eliminar/', views.evento_eliminar, name='evento_eliminar'),
]
