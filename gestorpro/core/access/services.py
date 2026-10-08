"""
Servicios de acceso: alta de empresas y membresías.

Toda escritura que involucra varias entidades ocurre dentro de una transacción.
"""
import uuid

from django.db import transaction
from django.utils.text import slugify

from gestorpro.core.tenancy.context import tenant_context
from gestorpro.core.tenancy.models import Location, Tenant

from .defaults import SYSTEM_ROLES, expand
from .models import Membership, Permission, Role


def _unique_slug(name: str) -> str:
    base = slugify(name)[:40] or 'empresa'
    slug = base
    while Tenant.objects.filter(slug=slug).exists():
        slug = f'{base}-{uuid.uuid4().hex[:6]}'
    return slug


def create_system_roles(tenant) -> dict[str, Role]:
    """Crea (o actualiza) los roles de sistema. Requiere el tenant activo."""
    catalog = set(Permission.objects.values_list('code', flat=True))
    roles = {}
    for code, spec in SYSTEM_ROLES.items():
        role, _ = Role.objects.update_or_create(
            code=code,
            defaults={'name': spec['name'], 'is_system': True, 'grants_all': spec.get('grants_all', False)},
        )
        role.permissions.set(expand(spec['permissions'], catalog))
        roles[code] = role
    return roles


@transaction.atomic
def provision_tenant(*, name: str, owner, vertical: str = Tenant.Vertical.GENERIC, **tenant_fields) -> Tenant:
    """Alta completa de una empresa: tenant + sucursal principal + roles + OWNER."""
    tenant = Tenant.objects.create(name=name, slug=_unique_slug(name), vertical=vertical, **tenant_fields)
    with tenant_context(tenant):
        location = Location.objects.create(name='Principal', is_default=True)
        roles = create_system_roles(tenant)
        Membership.objects.create(user=owner, role=roles['OWNER'], default_location=location)
    return tenant


@transaction.atomic
def add_member(*, user, role_code: str, status=Membership.Status.ACTIVE) -> Membership:
    """Agrega un usuario a la empresa activa con el rol indicado."""
    role = Role.objects.get(code=role_code)
    location = Location.objects.filter(is_default=True).first()
    return Membership.objects.create(user=user, role=role, status=status, default_location=location)


def active_memberships_for(user):
    """
    Membresías activas de un usuario en TODAS sus empresas.
    Acceso no filtrado explícito: se usa para login y selector de empresa.
    """
    return (
        Membership.all_tenants
        .select_related('tenant', 'role')
        .filter(user=user, status=Membership.Status.ACTIVE, tenant__status=Tenant.Status.ACTIVE)
        .order_by('tenant__name')
    )
