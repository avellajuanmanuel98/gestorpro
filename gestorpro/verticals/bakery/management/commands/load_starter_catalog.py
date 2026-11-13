"""
Carga el catálogo base de ingredientes en una panadería existente.

    python manage.py load_starter_catalog panaderia-la-favorita

Crea las categorías de ingredientes y unos 30 ingredientes comunes (harina,
huevos, queso costeño, empaques…) SIN costos ni existencias: cada panadería
registra los suyos. Es idempotente: no duplica ni modifica lo que ya exista.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gestorpro.core.tenancy.context import tenant_context
from gestorpro.core.tenancy.models import Tenant
from gestorpro.verticals.bakery.catalog import load_starter_ingredients
from gestorpro.verticals.bakery.definition import MIGA


class Command(BaseCommand):
    help = 'Carga los ingredientes comunes de panadería en una empresa.'

    def add_arguments(self, parser):
        parser.add_argument('slug', help='Identificador de la empresa (ver: manage.py set_plan --list)')

    def handle(self, *args, **opts):
        tenant = Tenant.objects.filter(slug=opts['slug']).first()
        if tenant is None:
            raise CommandError(f'No existe la empresa {opts["slug"]}.')
        if tenant.vertical != MIGA.key:
            raise CommandError('Esa empresa no es una panadería.')
        with transaction.atomic(), tenant_context(tenant):
            created = load_starter_ingredients()
        self.stdout.write(self.style.SUCCESS(f'{tenant.name}: {created} ingredientes creados.'))
