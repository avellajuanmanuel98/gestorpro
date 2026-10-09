"""Consumo de los límites del plan por la empresa activa."""
from gestorpro.core import entitlements
from gestorpro.core.tenancy.context import get_active_tenant_id


def current_usage() -> dict[str, int]:
    # Imports diferidos: este módulo agrega datos de varias apps del Core.
    from gestorpro.core.access.models import Role
    from gestorpro.core.access.services import seats_in_use
    from gestorpro.core.catalog.services import products_count
    from gestorpro.core.tenancy.models import Location

    return {
        'users': seats_in_use(),
        'locations': Location.objects.filter(is_active=True).count(),
        'products': products_count(),
        'custom_roles': Role.objects.filter(is_system=False).count(),
    }


def plan_summary() -> dict:
    ent = entitlements.for_tenant(get_active_tenant_id())
    usage = current_usage()
    return {
        'plan': {'code': ent.plan_code, 'name': ent.plan_name, 'status': ent.status,
                 'trial_ends_at': ent.trial_ends_at},
        'features': sorted(ent.features),
        'limits': [
            {'key': key, 'label': label, 'used': usage.get(key, 0), 'limit': ent.limit(key)}
            for key, label in entitlements.LIMITS.items()
        ],
    }
