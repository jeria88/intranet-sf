from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    path('', views.index, name='index'),
    path('circular/nueva/', views.circular_crear, name='circular_crear'),
    path('circular/<int:pk>/aprobar/', views.circular_aprobar, name='circular_aprobar'),
    path('circular/<int:pk>/', views.circular_detalle, name='circular_detalle'),
]
