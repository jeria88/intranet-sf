from django.urls import path
from . import views

app_name = 'simce'

urlpatterns = [
    # Admin
    path('',                          views.admin_dashboard,    name='admin_dashboard'),
    path('generar/',                  views.admin_generar,      name='admin_generar'),
    path('revisar/<int:pk>/',         views.admin_revisar,      name='admin_revisar'),
    path('aprobar/<int:pk>/',         views.admin_aprobar,      name='admin_aprobar'),
    path('publicar/<int:pk>/',        views.admin_publicar,     name='admin_publicar'),

    # Estudiante
    path('rendir/<int:pk>/',          views.prueba_identificacion, name='prueba_identificacion'),
    path('sesion/<int:sesion_pk>/',   views.prueba_rendir,         name='prueba_rendir'),
    path('resultado/<int:sesion_pk>/',views.prueba_resultado,      name='prueba_resultado'),

    # Reportes
    path('reportes/',                 views.reportes_dashboard,  name='reportes_dashboard'),
    path('reportes/<int:pk>/',        views.reporte_prueba,      name='reporte_prueba'),
    path('reportes/estudiante/<int:sesion_pk>/', views.reporte_estudiante, name='reporte_estudiante'),
]
