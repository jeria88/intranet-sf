from django.urls import path
from . import views

app_name = 'ai_modules'

urlpatterns = [
    path('', views.ai_list, name='ai_list'),
    path('mis-consultas/', views.mis_consultas, name='mis_consultas'),
    path('mis-consultas/<int:pk>/', views.consulta_detalle, name='consulta_detalle'),
    path('admin/cola/', views.cola_consultas, name='cola_consultas'),
    path('admin/consulta/<int:pk>/', views.responder_consulta, name='responder_consulta'),
    path('<slug:slug>/', views.ai_detail, name='ai_detail'),
    path('<slug:slug>/consultar/', views.nueva_consulta, name='nueva_consulta'),
    path('<slug:slug>/chat/', views.ai_chat, name='ai_chat'),
    path('notebooklm/instrucciones/', views.notebooklm_instruction, name='notebooklm_instruction'),
    
    # Repositorio de Casos
    path('casos/repositorio/', views.case_repository, name='case_repository'),
    path('casos/guardar/', views.save_as_case, name='save_as_case'),
    path('casos/<int:pk>/cambiar-estado/', views.toggle_case_status, name='toggle_case_status'),
    path('casos/<int:pk>/generar-descargos/', views.generate_case_defense, name='generate_case_defense'),
]
