from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    """
    GET /api/health/ → {"ok": true}. Para el chequeo de salud del proveedor (Render) y un
    monitor externo que mantenga la app despierta. No consulta la base ni requiere sesión.
    """
    return JsonResponse({'ok': True})
