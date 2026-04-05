from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.bandeja_entrada, name='bandeja_entrada'),
    path('enviados/', views.bandeja_enviados, name='bandeja_enviados'),
    path('nuevo/', views.mensaje_nuevo, name='mensaje_nuevo'),
    path('<int:pk>/', views.mensaje_detalle, name='mensaje_detalle'),
    path('<int:pk>/responder/', views.mensaje_responder, name='mensaje_responder'),
]
