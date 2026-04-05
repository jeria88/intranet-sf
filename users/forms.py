from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import User


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'profile_picture', 'bio', 'phone']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }


class DemoAuthenticationForm(AuthenticationForm):
    """Formulario para permitir login con contraseña vacía en el demo."""
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
        required=False,
    )

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username == "l.jeria" and not password:
            try:
                self.user_cache = User.objects.get(username=username)
                self.confirm_login_allowed(self.user_cache)
                return self.cleaned_data
            except User.DoesNotExist:
                pass
        
        return super().clean()
