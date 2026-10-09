"""
Empresas creadas antes de existir los planes no tienen suscripción y, por
diseño fail-closed, quedarían sin funcionalidades y con límites en 0.
Se les asigna una prueba del plan por defecto. Idempotente.
"""
import datetime

from django.conf import settings
from django.db import migrations
from django.utils import timezone


def backfill(apps, schema_editor):
    Tenant = apps.get_model('tenancy', 'Tenant')
    Plan = apps.get_model('subscriptions', 'Plan')
    Subscription = apps.get_model('subscriptions', 'Subscription')
    plan = Plan.objects.filter(code=getattr(settings, 'DEFAULT_PLAN_CODE', 'starter')).first()
    if plan is None:
        return
    now = timezone.now()
    trial_end = now + datetime.timedelta(days=14)
    for tenant in Tenant.objects.filter(subscription__isnull=True):
        Subscription.objects.create(tenant=tenant, plan=plan, status='trialing', started_at=now,
                                    trial_ends_at=trial_end, current_period_end=trial_end)


class Migration(migrations.Migration):
    dependencies = [('subscriptions', '0002_seed_plans'), ('tenancy', '0001_initial')]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
