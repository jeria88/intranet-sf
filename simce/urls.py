from django.urls import path
from . import views

app_name = 'simce'

urlpatterns = [
    # Admin
    path('',                              views.admin_dashboard,       name='admin_dashboard'),
    path('generar/',                      views.admin_generar,         name='admin_generar'),
    path('generando/<int:pk>/',           views.prueba_generando,      name='prueba_generando'),
    path('api/estado/<int:pk>/',          views.api_estado_prueba,     name='api_estado_prueba'),
    path('revisar-textos/<int:pk>/',      views.admin_revisar_textos,  name='admin_revisar_textos'),
    path('api/ajustar/<int:pk>/',         views.api_ajustar_texto,     name='api_ajustar_texto'),
    path('api/estado-texto/<int:pk>/',    views.api_estado_texto,      name='api_estado_texto'),
    path('lanzar-preguntas/<int:pk>/',    views.admin_lanzar_preguntas,name='admin_lanzar_preguntas'),
    path('revisar/<int:pk>/',             views.admin_revisar,         name='admin_revisar'),
    path('aprobar/<int:pk>/',             views.admin_aprobar,         name='admin_aprobar'),
    path('publicar/<int:pk>/',            views.admin_publicar,        name='admin_publicar'),
    path('eliminar/<int:pk>/',            views.admin_eliminar,        name='admin_eliminar'),

    # Estudiante — el modo va en la URL para que el profe comparta el link correcto
    path('rendir/<int:pk>/<str:modo>/',                              views.prueba_identificacion, name='prueba_identificacion'),
    path('sesion/<int:sesion_pk>/',                                  views.prueba_rendir,         name='prueba_rendir'),
    path('sesion/<int:sesion_pk>/verificar/<int:pregunta_pk>/',      views.verificar_respuesta,   name='verificar_respuesta'),
    path('sesion/<int:sesion_pk>/finalizar/',                        views.finalizar_prueba,      name='finalizar_prueba'),
    path('sesion/<int:sesion_pk>/entregar/',                         views.entregar_simce,        name='entregar_simce'),
    path('resultado/<int:sesion_pk>/',                               views.prueba_resultado,      name='prueba_resultado'),

    # Reportes
    path('reportes/',                 views.reportes_dashboard,  name='reportes_dashboard'),
    path('reportes/<int:pk>/',        views.reporte_prueba,      name='reporte_prueba'),
    path('reportes/estudiante/<int:sesion_pk>/', views.reporte_estudiante, name='reporte_estudiante'),

    # CRUD API
    path('api/texto/<int:pk>/',       views.api_texto,           name='api_texto'),
    path('api/pregunta/<int:pk>/',    views.api_pregunta,        name='api_pregunta'),
    path('api/sesion/<int:pk>/',      views.api_sesion,          name='api_sesion'),
]
