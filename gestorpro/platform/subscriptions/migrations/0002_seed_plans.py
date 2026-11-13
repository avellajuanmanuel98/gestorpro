"""
Planes iniciales. Son una PROPUESTA editable desde /admin/ (Planes):
precios vacíos = por definir; límites y funcionalidades se ajustan sin código.
"""
from django.db import migrations

PLANS = [
    # code, name, sort, features, limits (None = ilimitado)
    ('starter', 'Starter', 1, [], {'users': 3, 'locations': 1, 'products': 150, 'custom_roles': 0}),
    ('business', 'Business', 2, ['module.hr', 'custom_roles'],
     {'users': 10, 'locations': 2, 'products': 1000, 'custom_roles': 3}),
    ('pro', 'Pro', 3, ['module.hr', 'module.assistant', 'custom_roles'],
     {'users': None, 'locations': 5, 'products': None, 'custom_roles': None}),
]


def seed(apps, schema_editor):
    Plan = apps.get_model('subscriptions', 'Plan')
    PlanFeature = apps.get_model('subscriptions', 'PlanFeature')
    PlanLimit = apps.get_model('subscriptions', 'PlanLimit')
    for code, name, sort, features, limits in PLANS:
        plan, _ = Plan.objects.get_or_create(code=code, defaults={'name': name, 'sort': sort})
        for key in features:
            PlanFeature.objects.get_or_create(plan=plan, key=key)
        for key, value in limits.items():
            PlanLimit.objects.get_or_create(plan=plan, key=key, defaults={'value': value})


class Migration(migrations.Migration):
    dependencies = [('subscriptions', '0001_initial')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
