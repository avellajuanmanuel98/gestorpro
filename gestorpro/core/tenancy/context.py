"""
Contexto de tenant activo.

El tenant activo vive en un ContextVar: es local al hilo/tarea y se restablece
al terminar cada petición (TenantContextMiddleware). Todo acceso a datos de
negocio pasa por aquí; si no hay tenant activo, la operación FALLA en lugar de
devolver datos de todos los tenants.

Uso fuera de una petición HTTP (comandos, tareas, tests):

    with tenant_context(tenant):
        Customer.objects.create(...)
"""
from contextlib import contextmanager
from contextvars import ContextVar

from gestorpro.kernel.errors import TenantContextMissing

_active_tenant_id: ContextVar[int | None] = ContextVar('active_tenant_id', default=None)


def get_active_tenant_id(required: bool = True) -> int | None:
    tenant_id = _active_tenant_id.get()
    if tenant_id is None and required:
        raise TenantContextMissing('No hay una empresa activa para esta operación.')
    return tenant_id


def activate(tenant_or_id):
    """Activa un tenant y devuelve el token para restaurar el estado previo."""
    tenant_id = getattr(tenant_or_id, 'pk', tenant_or_id)
    if tenant_id is None:
        raise TenantContextMissing('No se puede activar un tenant sin id.')
    return _active_tenant_id.set(int(tenant_id))


def deactivate_all():
    return _active_tenant_id.set(None)


def restore(token):
    _active_tenant_id.reset(token)


@contextmanager
def tenant_context(tenant_or_id):
    token = activate(tenant_or_id)
    try:
        yield
    finally:
        restore(token)


@contextmanager
def no_tenant_context():
    token = deactivate_all()
    try:
        yield
    finally:
        restore(token)
