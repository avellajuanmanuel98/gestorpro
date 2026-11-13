from django.utils.dateparse import parse_date
from rest_framework import generics

from gestorpro.core.access.permissions import HasTenantPermission

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    """
    GET /api/audit/ — registro de la empresa activa (solo lectura).
    Filtros: action (prefijo), actor (id), entity_type, entity_id, date_from, date_to (AAAA-MM-DD).
    """
    serializer_class = AuditLogSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'audit.view'}

    def get_queryset(self):
        qs = AuditLog.objects.all()
        params = self.request.query_params
        if params.get('action'):
            qs = qs.filter(action__startswith=params['action'])
        if params.get('actor'):
            qs = qs.filter(actor_id=params['actor'])
        if params.get('entity_type'):
            qs = qs.filter(entity_type=params['entity_type'])
        if params.get('entity_id'):
            qs = qs.filter(entity_id=params['entity_id'])
        if (start := parse_date(params.get('date_from') or '')) is not None:
            qs = qs.filter(created_at__date__gte=start)
        if (end := parse_date(params.get('date_to') or '')) is not None:
            qs = qs.filter(created_at__date__lte=end)
        return qs
