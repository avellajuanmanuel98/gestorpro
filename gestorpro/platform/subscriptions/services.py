import datetime

from django.conf import settings
from django.utils import timezone

from gestorpro.core.entitlements import Entitlements

from .models import Plan, Subscription

TRIAL_DAYS = 14


def entitlements_for(tenant_id: int) -> Entitlements | None:
    """Proveedor de entitlements para el Core (registrado en apps.py)."""
    sub = (
        Subscription.objects.select_related('plan')
        .prefetch_related('plan__features', 'plan__limits')
        .filter(tenant_id=tenant_id)
        .first()
    )
    if sub is None or sub.status == Subscription.Status.CANCELED:
        return None
    return Entitlements(
        plan_code=sub.plan.code,
        plan_name=sub.plan.name,
        status=sub.status,
        trial_ends_at=sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
        features=frozenset(f.key for f in sub.plan.features.all()),
        limits={lim.key: lim.value for lim in sub.plan.limits.all()},
    )


def on_tenant_provisioned(sender, tenant, plan_code=None, **kwargs):
    """Toda empresa nueva arranca con una suscripción (por defecto, prueba del plan configurado)."""
    plan = Plan.objects.get(code=plan_code or settings.DEFAULT_PLAN_CODE, is_active=True)
    now = timezone.now()
    trial_end = now + datetime.timedelta(days=TRIAL_DAYS)
    Subscription.objects.create(
        tenant=tenant, plan=plan, status=Subscription.Status.TRIALING,
        started_at=now, trial_ends_at=trial_end, current_period_end=trial_end,
    )
