from django.urls import path
from . import views

app_name = 'meetings'

urlpatterns = [
    path('', views.meeting_list, name='meeting_list'),
    path('repositorio/', views.recording_list, name='recording_list'),
    path('sync/', views.sync_daily_recordings, name='sync_daily_recordings'),
    path('webhook/recording/', views.recording_webhook, name='recording_webhook'),
    path('webhook/recording', views.recording_webhook),
    path('webhook/register/', views.register_daily_webhook, name='register_daily_webhook'),
    path('<slug:slug>/', views.meeting_room, name='meeting_room'),
    path('<slug:slug>/reservar/', views.booking_crear, name='booking_crear'),
    path('reserva/<int:pk>/', views.booking_detalle, name='booking_detalle'),
    path('reserva/<int:pk>/editar/', views.meeting_edit, name='meeting_edit'),
    path('reserva/<int:pk>/eliminar/', views.meeting_delete, name='meeting_delete'),
    path('manual/nueva/', views.meeting_create_manual, name='meeting_create_manual'),
    path('reserva/<int:pk>/grabar/', views.start_recording, name='start_recording'),
    path('recording/<int:pk>/download/', views.download_recording, name='download_recording'),

    
    # API para GitHub Actions
    path('api/pending/', views.api_pending_meetings, name='api_pending_meetings'),
    path('api/update/<int:pk>/', views.api_update_meeting, name='api_update_meeting'),
    path('api/start/<int:pk>/', views.api_start_processing, name='api_start_processing'),
    
    # Reportes
    path('reserva/<int:pk>/participantes-pdf/', views.participants_report_print, name='participants_pdf'),
    path('reserva/<int:pk>/acta-pdf/', views.acta_report_print, name='acta_pdf'),
    path('reserva/<int:pk>/acuerdos-pdf/', views.acuerdos_report_print, name='acuerdos_pdf'),
]
