"""
API de la consola de plataforma (/api/platform/). Solo personal de GestorPro
(`is_platform_admin`). No usa contexto de empresa: consulta de forma explícita.
"""
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from gestorpro.core.access.permissions import IsPlatformAdmin
from gestorpro.core.audit.context import client_ip
from gestorpro.platform.subscriptions.models import Plan

from . import serializers as s
from . import services
from .models import PlatformEvent


class PlatformView(APIView):
    permission_classes = [IsPlatformAdmin]

    def ip(self):
        return client_ip(self.request)


class OverviewView(PlatformView):
    def get(self, request):
        return Response(services.overview())


class TenantListView(PlatformView, generics.ListAPIView):
    serializer_class = s.TenantRowSerializer

    def get_queryset(self):
        return services.tenant_queryset(self.request.query_params)

    def post(self, request):
        data = s.OnboardSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        d = data.validated_data
        tenant, url = services.onboard(request.user, name=d['name'], owner_email=d['owner_email'],
                                       vertical=d['vertical'], plan_code=d['plan'], city=d['city'],
                                       tax_id=d['tax_id'], ip=self.ip())
        row = services.tenant_queryset({}).get(pk=tenant.pk)
        return Response({'tenant': s.TenantRowSerializer(row).data, 'invitation_url': url},
                        status=status.HTTP_201_CREATED)


class TenantDetailView(PlatformView):
    def tenant(self, pk):
        return get_object_or_404(services.tenant_queryset({}), pk=pk)

    def get(self, request, pk):
        tenant = self.tenant(pk)
        return Response({**s.TenantRowSerializer(tenant).data, **services.tenant_detail(tenant)})


class TenantStatusView(TenantDetailView):
    def post(self, request, pk):
        data = s.TenantStatusSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.set_tenant_status(request.user, self.tenant(pk), data.validated_data['status'],
                                   data.validated_data['reason'], ip=self.ip())
        return self.get(request, pk)


class TenantSubscriptionView(TenantDetailView):
    def patch(self, request, pk):
        data = s.SubscriptionChangeSerializer(data=request.data, partial=True)
        data.is_valid(raise_exception=True)
        services.change_subscription(request.user, self.tenant(pk), data.validated_data, ip=self.ip())
        return self.get(request, pk)


class TenantReinviteView(TenantDetailView):
    def post(self, request, pk):
        data = s.EmailSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        url = services.reinvite_owner(request.user, self.tenant(pk), data.validated_data['email'], ip=self.ip())
        return Response({'invitation_url': url})


class SupportStartView(TenantDetailView):
    def post(self, request, pk):
        data = s.ReasonSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        result = services.start_support(request.user, self.tenant(pk), data.validated_data['reason'], ip=self.ip())
        return Response(result, status=status.HTTP_201_CREATED)


class SupportEndView(PlatformView):
    """Cierra la sesión de soporte. Se puede llamar con el token de soporte (está en la lista permitida)."""

    def post(self, request):
        session_id = (request.auth or {}).get('sup') if request.auth else None
        session_id = session_id or request.data.get('session')
        ended = services.end_support(request.user, int(session_id), ip=self.ip()) if session_id else False
        return Response({'ended': ended})


class PlanListView(PlatformView, generics.ListAPIView):
    serializer_class = s.PlanSerializer
    pagination_class = None

    def get_queryset(self):
        return Plan.objects.prefetch_related('features', 'limits').annotate(subscribers=Count('subscriptions'))


class PlanDetailView(PlatformView):
    def patch(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        data = s.PlanUpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        services.update_plan(request.user, plan, data.validated_data, ip=self.ip())
        plan = PlanListView().get_queryset().get(pk=pk)
        return Response(s.PlanSerializer(plan).data)


class EventListView(PlatformView, generics.ListAPIView):
    serializer_class = s.PlatformEventSerializer

    def get_queryset(self):
        qs = PlatformEvent.objects.select_related('tenant')
        p = self.request.query_params
        if p.get('tenant'):
            qs = qs.filter(tenant_id=p['tenant'])
        if p.get('action'):
            qs = qs.filter(action__startswith=p['action'])
        return qs
