from django.urls import path
from . import views

app_name = 'improvement_cycle'

urlpatterns = [
    path('', views.dashboard_ee, name='dashboard_ee'),
    path('red/', views.dashboard_red, name='dashboard_red'),
    path('alertas/', views.alertas_activas, name='alertas_activas'),
    path('meta/nueva/', views.meta_crear, name='meta_crear'),
    path('meta/<int:pk>/', views.goal_detail, name='goal_detail'),
    path('meta/<int:pk>/editar/', views.goal_edit, name='goal_edit'),
    path('meta/<int:pk>/eliminar/', views.goal_delete, name='goal_delete'),
    path('meta/<int:goal_pk>/accion/nueva/', views.action_create, name='action_create'),

    path('accion/<int:pk>/toggle/', views.action_toggle, name='action_toggle'),
]
