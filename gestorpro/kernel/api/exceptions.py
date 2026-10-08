import logging

from rest_framework.exceptions import PermissionDenied
from rest_framework.views import exception_handler as drf_exception_handler

from gestorpro.kernel.errors import TenantIsolationError

logger = logging.getLogger('gestorpro.security')


def exception_handler(exc, context):
    """
    Un fallo de aislamiento nunca se convierte en 500 con detalles internos:
    se registra como evento de seguridad y se responde 403 genérico.
    """
    if isinstance(exc, TenantIsolationError):
        view = context.get('view')
        logger.warning('tenant_isolation_error view=%s error=%s', type(view).__name__, exc)
        exc = PermissionDenied('No tienes acceso a este recurso en la empresa activa.')
    return drf_exception_handler(exc, context)
