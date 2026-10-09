"""
Servicios de acceso: alta de empresas, membresías, invitaciones y roles.

Reglas de seguridad que se aplican aquí (no en el frontend):
- Nadie puede otorgar permisos que no tiene (anti-escalada). OWNER es la
  única excepción porque los tiene todos.
- Solo un OWNER puede asignar el rol OWNER o modificar a otro OWNER.
- Nadie puede modificar ni eliminar su propia membresía (evita auto-bloqueos).
- Siempre queda al menos un OWNER activo.
- Los límites del plan (usuarios, roles personalizados) se validan aquí.
Toda escritura ocurre en una transacción y queda en el registro de auditoría.
"""
import datetime
import hashlib
import secrets
import uuid

from django.contrib.auth import authenticate, get_user_model, password_validation
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import PermissionDenied, ValidationError

from gestorpro.core import entitlements
from gestorpro.core.audit import services as audit
from gestorpro.core.audit.context import bind_actor
from gestorpro.core.tenancy.context import get_active_tenant_id, tenant_context
from gestorpro.core.tenancy.models import Location, Tenant
from gestorpro.core.tenancy.signals import tenant_provisioned

from .defaults import SYSTEM_ROLES, expand
from .models import Invitation, Membership, Permission, Role

INVITATION_DAYS = 7


# ── Alta de empresas ──────────────────────────────────────────────────────────

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
def provision_tenant(*, name: str, owner, vertical: str = Tenant.Vertical.GENERIC,
                     plan_code: str | None = None, **tenant_fields) -> Tenant:
    """
    Alta completa de una empresa: tenant + sucursal principal + roles + OWNER.
    Luego emite `tenant_provisioned` (suscripción, configuración del vertical)
    dentro de la misma transacción: si algo falla, no queda una empresa a medias.
    """
    tenant = Tenant.objects.create(name=name, slug=_unique_slug(name), vertical=vertical, **tenant_fields)
    with tenant_context(tenant):
        location = Location.objects.create(name='Principal', is_default=True)
        roles = create_system_roles(tenant)
        Membership.objects.create(user=owner, role=roles['OWNER'], default_location=location)
        tenant_provisioned.send(sender=Tenant, tenant=tenant, plan_code=plan_code)
    return tenant


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


# ── Reglas de autorización sobre roles ────────────────────────────────────────

def _is_owner(membership) -> bool:
    return membership.role.grants_all


def _assert_can_grant(actor, role: Role):
    """Anti-escalada: el rol asignado no puede tener permisos que el actor no tiene."""
    if _is_owner(actor):
        return
    if role.grants_all:
        raise PermissionDenied('Solo un propietario puede asignar el rol de propietario.')
    missing = role.permission_codes() - actor.permission_codes
    if missing:
        raise PermissionDenied('No puedes asignar un rol con permisos que tú no tienes.')


def _assert_can_grant_codes(actor, codes: set[str]):
    if _is_owner(actor):
        return
    if codes - actor.permission_codes:
        raise PermissionDenied('No puedes otorgar permisos que tú no tienes.')


def _assert_keeps_an_owner(target: Membership, new_role: Role | None = None, new_status: str | None = None,
                           removing: bool = False):
    if not _is_owner(target):
        return
    stays_owner = not removing and (new_role is None or new_role.grants_all) and \
        (new_status in (None, Membership.Status.ACTIVE))
    if stays_owner:
        return
    others = Membership.objects.filter(role__grants_all=True, status=Membership.Status.ACTIVE) \
        .exclude(pk=target.pk).exists()
    if not others:
        raise ValidationError('La empresa debe tener al menos un propietario activo.')


def _assert_can_manage(actor, target: Membership):
    if target.user_id == actor.user_id:
        raise PermissionDenied('No puedes modificar tu propio acceso.')
    if _is_owner(target) and not _is_owner(actor):
        raise PermissionDenied('Solo un propietario puede modificar a otro propietario.')


# ── Límite de usuarios ────────────────────────────────────────────────────────

def seats_in_use() -> int:
    """Miembros activos + invitaciones pendientes de la empresa activa."""
    pending = Invitation.objects.filter(accepted_at__isnull=True, revoked_at__isnull=True,
                                        expires_at__gt=timezone.now()).count()
    return Membership.objects.filter(status=Membership.Status.ACTIVE).count() + pending


def _check_seat_available():
    entitlements.check_limit(get_active_tenant_id(), 'users', seats_in_use())


# ── Membresías ────────────────────────────────────────────────────────────────

@transaction.atomic
def add_member(*, user, role_code: str, status=Membership.Status.ACTIVE) -> Membership:
    """Agrega un usuario a la empresa activa con el rol indicado (uso interno: seeds, invitaciones)."""
    role = Role.objects.get(code=role_code)
    location = Location.objects.filter(is_default=True).first()
    return Membership.objects.create(user=user, role=role, status=status, default_location=location)


@transaction.atomic
def update_member(*, actor: Membership, member: Membership, role: Role | None = None,
                  status: str | None = None) -> Membership:
    member = Membership.objects.select_for_update().select_related('role', 'user').get(pk=member.pk)
    _assert_can_manage(actor, member)
    if role is not None and role.pk != member.role_id:
        _assert_can_grant(actor, role)
    _assert_keeps_an_owner(member, new_role=role, new_status=status)
    if status == Membership.Status.ACTIVE and member.status != Membership.Status.ACTIVE:
        _check_seat_available()

    changes = {}
    if role is not None and role.pk != member.role_id:
        changes['role'] = [member.role.name, role.name]
        member.role = role
    if status is not None and status != member.status:
        changes['status'] = [member.status, status]
        member.status = status
    if changes:
        member.save()
        audit.record('access.member.updated', target=member, changes=changes,
                     summary=f'Modificó el acceso de {member.user.email}: '
                             + ', '.join(f'{k} {a} → {b}' for k, (a, b) in changes.items()))
    return member


@transaction.atomic
def remove_member(*, actor: Membership, member: Membership):
    member = Membership.objects.select_for_update().select_related('role', 'user').get(pk=member.pk)
    _assert_can_manage(actor, member)
    _assert_keeps_an_owner(member, removing=True)
    email, pk = member.user.email, member.pk
    member.delete()
    audit.record('access.member.removed', entity_type='access.membership', entity_id=str(pk),
                 summary=f'Quitó el acceso de {email} a la empresa')


# ── Invitaciones ──────────────────────────────────────────────────────────────

def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@transaction.atomic
def invite(*, actor: Membership, email: str, role: Role) -> tuple[Invitation, str]:
    """Crea una invitación y devuelve el token en claro (solo esta vez)."""
    email = email.strip().lower()
    _assert_can_grant(actor, role)
    if Membership.objects.filter(user__email__iexact=email).exists():
        raise ValidationError({'email': 'Esa persona ya pertenece a la empresa.'})
    now = timezone.now()
    # Una invitación vigente por email: la anterior se revoca
    Invitation.objects.filter(email__iexact=email, accepted_at__isnull=True, revoked_at__isnull=True) \
        .update(revoked_at=now)
    _check_seat_available()
    token = secrets.token_urlsafe(32)
    invitation = Invitation.objects.create(
        email=email, role=role, token_hash=_hash(token), invited_by=actor.user,
        expires_at=now + datetime.timedelta(days=INVITATION_DAYS),
    )
    audit.record('access.invitation.created', target=invitation,
                 summary=f'Invitó a {email} con el rol {role.name}')
    return invitation, token


@transaction.atomic
def revoke_invitation(invitation: Invitation):
    invitation = Invitation.objects.select_for_update().get(pk=invitation.pk)
    if invitation.status != 'pending':
        raise ValidationError('La invitación ya no está pendiente.')
    invitation.revoked_at = timezone.now()
    invitation.save(update_fields=['revoked_at', 'updated_at'])
    audit.record('access.invitation.revoked', target=invitation, summary=f'Revocó la invitación de {invitation.email}')


def find_pending_invitation(token: str) -> Invitation | None:
    """Búsqueda sin tenant activo (el token identifica la empresa). Acceso global explícito."""
    invitation = Invitation.all_tenants.select_related('tenant', 'role').filter(token_hash=_hash(token)).first()
    if invitation is None or invitation.status != 'pending' or not invitation.tenant.is_active:
        return None
    return invitation


@transaction.atomic
def accept_invitation(*, token: str, password: str, first_name: str = '', last_name: str = ''):
    """
    Acepta una invitación. Si ya existe una cuenta con ese email, se exige su
    contraseña (prueba de identidad); si no, se crea la cuenta.
    Devuelve (user, tenant_id).
    """
    User = get_user_model()
    invitation = find_pending_invitation(token)
    if invitation is None:
        raise ValidationError('La invitación no es válida o ya expiró.')
    invitation = Invitation.all_tenants.select_for_update().get(pk=invitation.pk)
    user = User.objects.filter(email__iexact=invitation.email).first()
    if user is not None:
        if authenticate(email=user.email, password=password) is None:
            raise ValidationError({'password': 'Contraseña incorrecta para esta cuenta.'})
    else:
        if not first_name.strip():
            raise ValidationError({'first_name': 'Indica tu nombre.'})
        candidate = User(email=invitation.email, first_name=first_name, last_name=last_name)
        password_validation.validate_password(password, candidate)
        user = User.objects.create_user(email=invitation.email, password=password,
                                        first_name=first_name.strip(), last_name=last_name.strip())

    bind_actor(user)  # la acción la realiza la persona invitada
    with tenant_context(invitation.tenant_id):
        if Membership.objects.filter(user=user).exists():
            raise ValidationError('Ya perteneces a esta empresa.')
        location = Location.objects.filter(is_default=True).first()
        Membership.objects.create(user=user, role=invitation.role, default_location=location)
        invitation.accepted_at = timezone.now()
        invitation.accepted_by = user
        invitation.save(update_fields=['accepted_at', 'accepted_by', 'updated_at'])
        audit.record('access.invitation.accepted', target=invitation,
                     summary=f'{user.email} aceptó la invitación ({invitation.role.name})')
    user.last_tenant_id = invitation.tenant_id
    user.save(update_fields=['last_tenant'])
    return user, invitation.tenant_id


# ── Roles personalizados ──────────────────────────────────────────────────────

def _custom_role_count() -> int:
    return Role.objects.filter(is_system=False).count()


def _validate_codes(codes) -> set[str]:
    codes = set(codes)
    unknown = codes - set(Permission.objects.filter(code__in=codes).values_list('code', flat=True))
    if unknown:
        raise ValidationError({'permissions': f'Permisos desconocidos: {", ".join(sorted(unknown))}'})
    return codes


@transaction.atomic
def create_role(*, actor: Membership, name: str, permissions) -> Role:
    tenant_id = get_active_tenant_id()
    entitlements.require_feature(tenant_id, 'custom_roles')
    entitlements.check_limit(tenant_id, 'custom_roles', _custom_role_count())
    codes = _validate_codes(permissions)
    _assert_can_grant_codes(actor, codes)
    base = slugify(name).upper().replace('-', '_')[:30] or 'ROL'
    code = base
    while Role.objects.filter(code=code).exists():
        code = f'{base}_{uuid.uuid4().hex[:4].upper()}'
    role = Role.objects.create(code=code, name=name.strip(), is_system=False)
    role.permissions.set(codes)
    audit.record('access.role.created', target=role, changes={'permissions': [[], sorted(codes)]},
                 summary=f'Creó el rol {role.name}')
    return role


@transaction.atomic
def update_role(*, actor: Membership, role: Role, name: str | None = None, permissions=None) -> Role:
    role = Role.objects.select_for_update().get(pk=role.pk)
    if role.grants_all:
        raise ValidationError('El rol de propietario no se puede modificar.')
    changes = {}
    if name is not None and name.strip() != role.name:
        if role.is_system:
            raise ValidationError({'name': 'Los roles del sistema no se pueden renombrar.'})
        changes['name'] = [role.name, name.strip()]
        role.name = name.strip()
        role.save(update_fields=['name', 'updated_at'])
    if permissions is not None:
        codes = _validate_codes(permissions)
        current = set(role.permissions.values_list('code', flat=True))
        # Solo se exige tener los permisos que se AGREGAN; quitar siempre está permitido.
        _assert_can_grant_codes(actor, codes - current)
        if codes != current:
            role.permissions.set(codes)
            changes['permissions'] = [sorted(current), sorted(codes)]
    if changes:
        audit.record('access.role.updated', target=role, changes=changes, summary=f'Modificó el rol {role.name}')
    return role


@transaction.atomic
def delete_role(role: Role):
    role = Role.objects.select_for_update().get(pk=role.pk)
    if role.is_system:
        raise ValidationError('Los roles del sistema no se pueden eliminar.')
    if role.memberships.exists() or role.invitations.filter(accepted_at__isnull=True, revoked_at__isnull=True).exists():
        raise ValidationError('El rol tiene usuarios o invitaciones; reasígnalos antes de eliminarlo.')
    name, pk = role.name, role.pk
    role.delete()
    audit.record('access.role.deleted', entity_type='access.role', entity_id=str(pk), summary=f'Eliminó el rol {name}')
