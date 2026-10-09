"""
Cambia el plan de una empresa (operación de plataforma).

    python manage.py set_plan --list
    python manage.py set_plan <slug-de-la-empresa> <codigo-del-plan> [--active]
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from gestorpro.core.tenancy.models import Tenant
from gestorpro.platform.subscriptions.models import Plan, Subscription


class Command(BaseCommand):
    help = 'Asigna un plan a una empresa (o lista empresas y planes con --list).'

    def add_arguments(self, parser):
        parser.add_argument('tenant', nargs='?', help='slug de la empresa')
        parser.add_argument('plan', nargs='?', help='código del plan: starter | business | pro')
        parser.add_argument('--active', action='store_true', help='marcar la suscripción como activa (no prueba)')
        parser.add_argument('--list', action='store_true', help='listar empresas y planes')

    def handle(self, *args, **options):
        if options['list'] or not options['tenant']:
            self.stdout.write('Planes: ' + ', '.join(Plan.objects.values_list('code', flat=True)))
            for t in Tenant.objects.select_related('subscription__plan').order_by('name'):
                sub = getattr(t, 'subscription', None)
                plan = f'{sub.plan.code} ({sub.status})' if sub else 'sin suscripción'
                self.stdout.write(f'  {t.slug:40} {plan}')
            return
        try:
            tenant = Tenant.objects.get(slug=options['tenant'])
            plan = Plan.objects.get(code=options['plan'], is_active=True)
        except (Tenant.DoesNotExist, Plan.DoesNotExist) as exc:
            raise CommandError(f'No encontrado: {exc}') from exc
        with transaction.atomic():
            sub, _ = Subscription.objects.select_for_update().get_or_create(
                tenant=tenant, defaults={'plan': plan, 'started_at': timezone.now()},
            )
            sub.plan = plan
            if options['active']:
                sub.status = Subscription.Status.ACTIVE
            sub.save()
        self.stdout.write(self.style.SUCCESS(f'{tenant.name}: plan {plan.name} ({sub.get_status_display()})'))
