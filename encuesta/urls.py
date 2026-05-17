from django.urls import path
from . import views

app_name = 'encuesta'

urlpatterns = [
    path('', views.responder, name='responder'),
    path('gracias/', views.gracias, name='gracias'),
    path('resultados/', views.resultados, name='resultados'),
]
