from django.db import transaction
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from gestorpro.core.access.permissions import HasTenantPermission
from gestorpro.core.audit import services as audit

from .catalog import load_starter_ingredients
from .definition import MIGA


class StarterCatalogView(APIView):
    """
    POST /api/bakery/starter-catalog/ — carga los ingredientes comunes de panadería
    en la empresa activa (sin costos ni existencias). Idempotente.
    """
    permission_classes = [HasTenantPermission]
    required_permissions = {'POST': 'catalog.manage'}

    @transaction.atomic
    def post(self, request):
        if request.tenant.vertical != MIGA.key:
            raise NotFound()
        created = load_starter_ingredients()
        if created:
            audit.record('catalog.starter_loaded', summary=f'Cargó {created} ingredientes comunes de panadería')
        return Response({'created': created})


class ProductionSuggestionView(APIView):
    """GET /api/bakery/production-suggestion/?date=AAAA-MM-DD — cuánto producir (mismo día de semanas previas)."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'production.view'}

    def get(self, request):
        from datetime import datetime

        from rest_framework.exceptions import ValidationError

        from .suggestions import suggest

        if request.tenant.vertical != MIGA.key:
            raise NotFound()
        target = None
        if request.query_params.get('date'):
            try:
                target = datetime.strptime(request.query_params['date'], '%Y-%m-%d').date()
            except ValueError as exc:
                raise ValidationError({'date': 'Formato AAAA-MM-DD.'}) from exc
        return Response(suggest(request.tenant, target))
