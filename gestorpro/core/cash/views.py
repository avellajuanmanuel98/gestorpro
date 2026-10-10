from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from gestorpro.core.access.permissions import HasTenantPermission

from . import services
from .models import CashRegister, CashSession
from .serializers import (
    CashMovementSerializer,
    CashRegisterSerializer,
    CashSessionDetailSerializer,
    CashSessionSerializer,
    CloseSessionSerializer,
    MovementInputSerializer,
    OpenSessionSerializer,
)


def visible_sessions(request):
    """Sin `cash.manage` cada persona solo ve sus propios turnos."""
    qs = CashSession.objects.select_related('register', 'opened_by', 'closed_by')
    if not request.membership.has_perm('cash.manage'):
        qs = qs.filter(opened_by=request.user)
    return qs


class RegisterListView(generics.ListAPIView):
    serializer_class = CashRegisterSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'cash.operate'}
    pagination_class = None

    def get_queryset(self):
        return CashRegister.objects.select_related('location').filter(is_active=True)


class CurrentSessionView(APIView):
    """GET /api/cash/sessions/current/ — el turno abierto de quien consulta (o null)."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'cash.operate'}

    def get(self, request):
        session = services.current_session(request.user)
        return Response({'session': CashSessionDetailSerializer(session).data if session else None})


class SessionListCreateView(generics.ListCreateAPIView):
    serializer_class = CashSessionSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'cash.operate', 'POST': 'cash.operate'}

    def get_queryset(self):
        qs = visible_sessions(self.request)
        if self.request.query_params.get('status') in CashSession.Status.values:
            qs = qs.filter(status=self.request.query_params['status'])
        return qs

    def create(self, request, *args, **kwargs):
        data = OpenSessionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        session = services.open_session(user=request.user, register=data.validated_data['register'],
                                        opening_amount=data.validated_data['opening_amount'])
        return Response(CashSessionDetailSerializer(session).data, status=status.HTTP_201_CREATED)


class SessionDetailView(generics.RetrieveAPIView):
    serializer_class = CashSessionDetailSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'cash.operate'}

    def get_queryset(self):
        return visible_sessions(self.request).prefetch_related('movements__created_by', 'movements__sale')


class _SessionActionView(APIView):
    permission_classes = [HasTenantPermission]
    required_permissions = {'POST': 'cash.operate'}

    def get_session(self, pk):
        session = visible_sessions(self.request).filter(pk=pk).first()
        if session is None:
            raise NotFound()
        return session


class SessionMovementView(_SessionActionView):
    def post(self, request, pk):
        data = MovementInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        movement = services.add_movement(membership=request.membership, session=self.get_session(pk),
                                         **data.validated_data)
        return Response(CashMovementSerializer(movement).data, status=status.HTTP_201_CREATED)


class SessionCloseView(_SessionActionView):
    def post(self, request, pk):
        data = CloseSessionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        session = services.close_session(membership=request.membership, session=self.get_session(pk),
                                         **data.validated_data)
        return Response(CashSessionDetailSerializer(session).data)
