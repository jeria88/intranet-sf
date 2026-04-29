from django.urls import path
from . import views

app_name = 'calendar_red'

urlpatterns = [
    path('', views.calendario, name='calendario'),
    path('nuevo/', views.evento_crear, name='evento_crear'),
    path('<int:pk>/', views.evento_detalle, name='evento_detalle'),
    path('<int:pk>/editar/', views.evento_editar, name='evento_editar'),
    path('<int:pk>/eliminar/', views.evento_eliminar, name='evento_eliminar'),
]
