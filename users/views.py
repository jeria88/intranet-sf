from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import UserProfileForm

from django.contrib.auth import logout as django_logout

@login_required

def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('users:profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'users/profile.html', {'form': form})

def custom_logout(request):
    """
    Cierre de sesión coherente y amigable.
    """
    if request.user.is_authenticated:
        django_logout(request)
    return render(request, 'users/logout_success.html')
