from .context import deactivate_all, restore
from .rls import reset_global_access


class TenantContextMiddleware:
    """
    Cada petición empieza SIN tenant activo y, al terminar, el contexto se
    restablece. Con workers que reutilizan hilos (gunicorn), esto impide que el
    tenant de una petición se filtre a la siguiente.

    El tenant lo activa la autenticación (TenantJWTAuthentication) solo después
    de verificar una membresía activa en base de datos.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = deactivate_all()
        access = reset_global_access()  # tampoco se hereda un acceso global (RLS) de otra petición
        try:
            return self.get_response(request)
        finally:
            restore(token)
            access.restore()
