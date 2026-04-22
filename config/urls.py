from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('portal.urls')),
    path('mensajes/', include('messaging.urls')),
    path('calendario/', include('calendar_red.urls')),
    path('salas/', include('meetings.urls')),
    path('biblioteca/', include('library.urls')),
    path('ia/', include('ai_modules.urls')),
    path('evidencia/', include('evidencia.urls')),
    path('mejora/', include('improvement_cycle.urls')),
    path('notificaciones/', include('notifications.urls')),
    path('usuarios/', include('users.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
