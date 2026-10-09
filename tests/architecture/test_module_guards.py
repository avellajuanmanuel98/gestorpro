"""
Guardianes de arquitectura: fallan si un módulo nuevo olvida el aislamiento.

- Todo modelo de las apps de GestorPro debe heredar TenantModel, salvo una
  lista explícita y justificada de entidades globales.
- Toda vista de negocio debe declarar un permiso existente por cada método.
"""
import pytest
from django.apps import apps
from django.urls import get_resolver

from gestorpro.core.access.permissions import HasTenantPermission
from gestorpro.core.access.registry import collect_permissions
from gestorpro.core.tenancy.db import TenantModel

pytestmark = [pytest.mark.isolation]

GLOBAL_MODELS = {
    'tenancy.Tenant': 'Es el propio tenant.',
    'identity.User': 'Identidad global; el vínculo con empresas es access.Membership.',
    'access.Permission': 'Catálogo de permisos definido en código.',
    'access.Role_permissions': 'Tabla intermedia M2M de Role (que sí es TenantModel).',
    'audit.SecurityEvent': 'Eventos de autenticación globales (p. ej. login fallido sin empresa); solo plataforma.',
    'subscriptions.Plan': 'Catálogo de planes de la plataforma.',
    'subscriptions.PlanFeature': 'Funcionalidades de un plan (plataforma).',
    'subscriptions.PlanLimit': 'Límites de un plan (plataforma).',
    'subscriptions.Subscription': 'La administra la plataforma; la empresa solo la lee vía entitlements.',
    'identity.User_groups': 'M2M de Django auth sobre el usuario global (solo admin de plataforma).',
    'identity.User_user_permissions': 'M2M de Django auth sobre el usuario global (solo admin de plataforma).',
}


def test_every_business_model_is_tenant_scoped():
    offenders = []
    for model in apps.get_models(include_auto_created=True):
        if not model._meta.app_config.name.startswith('gestorpro.'):
            continue
        label = f'{model._meta.app_label}.{model.__name__}'
        if label in GLOBAL_MODELS or issubclass(model, TenantModel):
            continue
        offenders.append(label)
    assert not offenders, f'Modelos sin tenant: {offenders}'


def _iter_views(resolver=None, prefix=''):
    resolver = resolver or get_resolver()
    for entry in resolver.url_patterns:
        if hasattr(entry, 'url_patterns'):
            yield from _iter_views(entry, prefix + str(entry.pattern))
        else:
            view = getattr(entry.callback, 'view_class', None) or getattr(entry.callback, 'cls', None)
            if view is not None:
                yield prefix + str(entry.pattern), view


def test_every_tenant_view_declares_known_permissions():
    catalog = collect_permissions()
    problems = []
    for route, view in _iter_views():
        perms = [p for p in getattr(view, 'permission_classes', [])]
        if not any(isinstance(p, type) and issubclass(p, HasTenantPermission) for p in perms):
            continue
        declared = getattr(view, 'required_permissions', {})
        if not declared:
            problems.append(f'{route}: sin required_permissions')
        for method, code in declared.items():
            if code not in catalog:
                problems.append(f'{route} {method}: permiso inexistente {code}')
    assert not problems, problems


def test_api_views_default_to_tenant_membership():
    """Un endpoint de /api/ sin permisos explícitos hereda IsTenantMember (fail-closed)."""
    from django.conf import settings
    assert settings.REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] == (
        'gestorpro.core.access.permissions.IsTenantMember',
    )
