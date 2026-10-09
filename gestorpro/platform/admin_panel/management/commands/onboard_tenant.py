"""
Alta de un CLIENTE real (operación de plataforma).

    python manage.py onboard_tenant "Panadería La Favorita" dueno@correo.com --vertical bakery --plan business

Crea la empresa (sucursal principal, roles, suscripción en prueba y
configuración del vertical) y una invitación de PROPIETARIO para el email
indicado. Imprime el enlace UNA sola vez: el dueño define su contraseña al
aceptarlo, así nadie más la conoce. No carga datos de demostración.

Si el enlace se pierde o vence, se puede regenerar:

    python manage.py onboard_tenant --reinvite <slug> dueno@correo.com
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction

from gestorpro.core.access.models import Membership
from gestorpro.core.access.services import invite_owner, provision_tenant
from gestorpro.core.tenancy.context import tenant_context
from gestorpro.core.tenancy.models import Tenant
from gestorpro.platform.subscriptions.models import Plan


class Command(BaseCommand):
    help = 'Da de alta un cliente y genera la invitación de su propietario.'

    def add_arguments(self, parser):
        parser.add_argument('name', nargs='?', help='Nombre comercial de la empresa')
        parser.add_argument('owner_email', nargs='?', help='Email del propietario')
        parser.add_argument('--vertical', default=Tenant.Vertical.BAKERY, choices=Tenant.Vertical.values)
        parser.add_argument('--plan', default=None, help='starter | business | pro (por defecto DEFAULT_PLAN_CODE)')
        parser.add_argument('--city', default='')
        parser.add_argument('--tax-id', default='', help='NIT')
        parser.add_argument('--reinvite', metavar='SLUG', help='Regenera la invitación del propietario de una empresa')

    def handle(self, *args, **opts):
        # Con --reinvite el único argumento posicional es el email
        email = (opts['owner_email'] or (opts['name'] if opts['reinvite'] else '') or '').strip()
        try:
            validate_email(email)
        except Exception as exc:
            raise CommandError('Indica un email de propietario válido.') from exc

        if opts['reinvite']:
            tenant = Tenant.objects.filter(slug=opts['reinvite']).first()
            if tenant is None:
                raise CommandError(f'No existe la empresa {opts["reinvite"]}.')
            with tenant_context(tenant):
                if Membership.objects.filter(role__grants_all=True, user__email__iexact=email).exists():
                    raise CommandError('Esa persona ya es propietaria de la empresa.')
                _, token = invite_owner(email=email)
            return self._print(tenant, email, token)

        if not opts['name']:
            raise CommandError('Indica el nombre de la empresa.')
        plan_code = opts['plan'] or settings.DEFAULT_PLAN_CODE
        if not Plan.objects.filter(code=plan_code, is_active=True).exists():
            raise CommandError(f'Plan desconocido: {plan_code}')
        if Tenant.objects.filter(name__iexact=opts['name']).exists():
            raise CommandError('Ya existe una empresa con ese nombre. '
                               'Usa --reinvite si solo necesitas un enlace nuevo.')

        with transaction.atomic():
            tenant = provision_tenant(name=opts['name'], vertical=opts['vertical'], plan_code=plan_code,
                                      city=opts['city'], tax_id=opts['tax_id'])
            with tenant_context(tenant):
                _, token = invite_owner(email=email)
        self._print(tenant, email, token)

    def _print(self, tenant, email, token):
        url = f"{settings.FRONTEND_URL.rstrip('/')}/invitation/{token}"
        self.stdout.write(self.style.SUCCESS(
            f'Empresa: {tenant.name} (slug: {tenant.slug}, vertical: {tenant.vertical})'))
        self.stdout.write(f'Invitación de propietario para {email} (vence en 7 días). Envíale este enlace:')
        self.stdout.write(f'\n  {url}\n')
        self.stdout.write(self.style.WARNING('El enlace solo se muestra ahora; no se guarda en claro.'))
