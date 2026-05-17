from django.shortcuts import redirect

EXEMPT_PREFIXES = (
    '/usuarios/cambiar-contrasena/',
    '/usuarios/logout/',
    '/admin/',
    '/static/',
    '/media/',
)


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and getattr(request.user, 'must_change_password', False)
            and not any(request.path.startswith(p) for p in EXEMPT_PREFIXES)
        ):
            return redirect('users:change_password')
        return self.get_response(request)
