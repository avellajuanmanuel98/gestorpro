"""
Funcionalidades y límites por plan (entitlements), vistos desde el Core.

El Core NO conoce los planes: pregunta por claves ('module.hr', 'users') a un
proveedor que registra la capa Platform al arrancar. Así los módulos del Core,
Capabilities y Verticals se pueden activar o limitar por plan sin importar
nada de Platform, y las restricciones viven en datos, no en código.

Fail-closed: si no hay proveedor o la empresa no tiene suscripción, no hay
funcionalidades opcionales y todos los límites valen 0.
"""
import logging
from dataclasses import dataclass, field

from rest_framework import status
from rest_framework.exceptions import APIException

logger = logging.getLogger('gestorpro.entitlements')

# Catálogo de claves conocidas. Platform valida contra él al editar planes.
FEATURES = {
    'module.hr': 'Módulo de personal (empleados)',
    'module.assistant': 'Asistente de IA',
    'custom_roles': 'Roles personalizados',
}
# Módulos (app label) que requieren una funcionalidad del plan
MODULE_FEATURES = {
    'hr': 'module.hr',
    'assistant': 'module.assistant',
}
# 'users' cuenta miembros activos + invitaciones pendientes.
LIMITS = {
    'users': 'Usuarios',
    'locations': 'Sucursales',
    'products': 'Productos',
    'custom_roles': 'Roles personalizados',
}


@dataclass(frozen=True)
class Entitlements:
    plan_code: str | None = None
    plan_name: str | None = None
    status: str | None = None
    trial_ends_at: str | None = None
    features: frozenset[str] = field(default_factory=frozenset)
    limits: dict[str, int | None] = field(default_factory=dict)  # None = ilimitado

    def has(self, feature: str) -> bool:
        return feature in self.features

    def limit(self, key: str) -> int | None:
        return self.limits.get(key, 0)


NONE = Entitlements()
_provider = None


def register_provider(provider):
    """provider(tenant_id) -> Entitlements. Lo llama Platform en AppConfig.ready()."""
    global _provider
    _provider = provider


def for_tenant(tenant_id: int) -> Entitlements:
    if _provider is None:
        logger.warning('entitlements_without_provider tenant=%s', tenant_id)
        return NONE
    return _provider(tenant_id) or NONE


class FeatureNotInPlan(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'feature_not_in_plan'
    default_detail = 'Tu plan actual no incluye esta funcionalidad.'


class PlanLimitReached(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = 'plan_limit_reached'


def require_feature(tenant_id: int, feature: str):
    if not for_tenant(tenant_id).has(feature):
        raise FeatureNotInPlan()


def check_limit(tenant_id: int, key: str, used: int, adding: int = 1):
    """Lanza PlanLimitReached si `used + adding` supera el límite del plan."""
    limit = for_tenant(tenant_id).limit(key)
    if limit is not None and used + adding > limit:
        raise PlanLimitReached(
            f'Tu plan permite {limit} {LIMITS.get(key, key).lower()}. Mejora tu plan para agregar más.'
        )
