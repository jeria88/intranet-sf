from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'evidencia'

urlpatterns = [
    path('', views.reuniones, name='reuniones'),
    path('presencial/', views.reunion_presencial, name='reunion_presencial'),
    path('virtual/', views.reunion_virtual, name='reunion_virtual'),
    path('formularios/', views.formularios, name='formularios'),
]
