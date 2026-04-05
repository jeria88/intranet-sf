from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.mis_notificaciones, name='mis_notificaciones'),
]
