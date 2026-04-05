from django.urls import path
from . import views

app_name = 'meetings'

urlpatterns = [
    path('', views.meeting_list, name='meeting_list'),
    path('repositorio/', views.recording_list, name='recording_list'),
    path('<slug:slug>/', views.meeting_room, name='meeting_room'),
    path('<slug:slug>/reservar/', views.booking_crear, name='booking_crear'),
    path('reserva/<int:pk>/', views.booking_detalle, name='booking_detalle'),
    path('reserva/<int:pk>/grabar/', views.start_recording, name='start_recording'),
]
