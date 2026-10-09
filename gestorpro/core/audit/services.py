"""
API de auditoría para el resto de módulos.

    from gestorpro.core.audit import services as audit
    audit.record('billing.invoice.created', target=invoice, summary='Creó la factura F-1')

Para CRUD genérico, las vistas base (core/api/views.py) llaman a
`record_created/updated/deleted` automáticamente. Los modelos pueden declarar:

    audit_sensitive_fields = {'salary'}          # se registra que cambió, no el valor
    audit_field_events = {'price': 'catalog.product.price_changed'}  # acción extra si cambia
"""
import datetime
from decimal import Decimal

from django.db import models
from django.db.models.fields.files import FieldFile

from gestorpro.core.tenancy.context import get_active_tenant_id

from .context import current
from .models import AuditLog, SecurityEvent

MASK = '••••'
IGNORED_FIELDS = {'id', 'tenant', 'created_at', 'updated_at', 'created_by'}


def _jsonable(value):
    if isinstance(value, Decimal):
        return format(value, 'f')
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, models.Model):
        return value.pk
    if isinstance(value, FieldFile):
        return value.name or None
    return value


def snapshot(instance) -> dict:
    """Valores actuales de los campos de negocio, listos para JSON."""
    data = {}
    for field in instance._meta.concrete_fields:
        if field.name in IGNORED_FIELDS:
            continue
        data[field.name] = _jsonable(getattr(instance, field.attname))
    return data


def diff(before: dict, after: dict, sensitive=frozenset()) -> dict:
    changes = {}
    for key in after.keys() | before.keys():
        if before.get(key) != after.get(key):
            changes[key] = [MASK, MASK] if key in sensitive else [before.get(key), after.get(key)]
    return changes


def _entity(target):
    if target is None:
        return '', ''
    return target._meta.label_lower, str(target.pk)


def record(action: str, *, summary: str, target=None, changes: dict | None = None,
           entity_type: str = '', entity_id: str = '') -> AuditLog | None:
    """Registra una acción en la empresa activa. Sin empresa activa no hay nada que auditar aquí."""
    if get_active_tenant_id(required=False) is None:
        return None
    ctx = current()
    if target is not None:
        entity_type, entity_id = _entity(target)
    return AuditLog.objects.create(
        actor_id=ctx.actor_id, actor_label=ctx.actor_label,
        action=action, entity_type=entity_type, entity_id=entity_id,
        summary=summary[:300], changes=changes or {},
        ip=ctx.ip, user_agent=ctx.user_agent,
    )


def security_event(kind: str, *, user=None, email: str = '', tenant_id: int | None = None):
    ctx = current()
    return SecurityEvent.objects.create(
        kind=kind, user=user, email=(email or getattr(user, 'email', ''))[:254],
        tenant_id_snapshot=tenant_id, ip=ctx.ip, user_agent=ctx.user_agent,
    )


# ── CRUD genérico ─────────────────────────────────────────────────────────────

def _label(instance) -> str:
    return f'{instance._meta.verbose_name} «{str(instance)[:80]}»'


def _action(instance, verb: str) -> str:
    return f'{instance._meta.label_lower}.{verb}'


def record_created(instance):
    record(_action(instance, 'created'), target=instance, summary=f'Creó {_label(instance)}',
           changes=diff({}, snapshot(instance), getattr(instance, 'audit_sensitive_fields', frozenset())))


def record_updated(instance, before: dict):
    sensitive = getattr(instance, 'audit_sensitive_fields', frozenset())
    changes = diff(before, snapshot(instance), sensitive)
    if not changes:
        return
    fields = ', '.join(str(instance._meta.get_field(f).verbose_name) for f in sorted(changes))
    record(_action(instance, 'updated'), target=instance, summary=f'Modificó {_label(instance)}: {fields}',
           changes=changes)
    for field, action in getattr(instance, 'audit_field_events', {}).items():
        if field in changes:
            old, new = changes[field]
            verbose = instance._meta.get_field(field).verbose_name
            record(action, target=instance, changes={field: [old, new]},
                   summary=f'Cambió {verbose} de {_label(instance)}: {old} → {new}')


def record_deleted(instance, before: dict, pk):
    record(_action(instance, 'deleted'), entity_type=instance._meta.label_lower, entity_id=str(pk),
           summary=f'Eliminó {_label(instance)}', changes={k: [v, None] for k, v in before.items()})
