from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import DemoAuthenticationForm

app_name = 'users'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='users/login.html',
        authentication_form=DemoAuthenticationForm
    ), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
]
