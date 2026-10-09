from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from gestorpro.core import entitlements
from gestorpro.core.audit import services as audit
from gestorpro.core.audit.context import bind_actor
from gestorpro.core.audit.models import SecurityEvent
from gestorpro.core.identity.tokens import issue_tokens

from . import services
from .models import Invitation, Membership, Permission, Role
from .permissions import HasTenantPermission
from .serializers import (
    AcceptInvitationSerializer,
    InvitationCreateSerializer,
    InvitationSerializer,
    MemberSerializer,
    MemberUpdateSerializer,
    PermissionSerializer,
    RoleSerializer,
    RoleWriteSerializer,
    invitation_url,
)


class MemberListView(generics.ListAPIView):
    """GET /api/access/members/ — usuarios de la empresa activa."""
    serializer_class = MemberSerializer
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'access.view'}

    def get_queryset(self):
        return Membership.objects.select_related('user', 'role').order_by('user__first_name', 'user__email')


class MemberDetailView(APIView):
    """PATCH/DELETE /api/access/members/<id>/ — cambiar rol/estado o quitar acceso."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'PATCH': 'access.manage_users', 'DELETE': 'access.manage_users'}

    def _member(self, pk):
        return generics.get_object_or_404(Membership.objects.select_related('user', 'role'), pk=pk)

    def patch(self, request, pk):
        serializer = MemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = services.update_member(actor=request.membership, member=self._member(pk), **serializer.validated_data)
        return Response(MemberSerializer(member).data)

    def delete(self, request, pk):
        services.remove_member(actor=request.membership, member=self._member(pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvitationListCreateView(APIView):
    """
    GET  /api/access/invitations/ — invitaciones pendientes.
    POST /api/access/invitations/ — crea una invitación. La respuesta incluye
         `invite_url` UNA sola vez (el token no se guarda en claro).
    """
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'access.view', 'POST': 'access.manage_users'}

    def get(self, request):
        pending = [i for i in Invitation.objects.select_related('role', 'invited_by') if i.status == 'pending']
        return Response(InvitationSerializer(pending, many=True).data)

    def post(self, request):
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation, token = services.invite(actor=request.membership, **serializer.validated_data)
        data = InvitationSerializer(invitation).data
        data['invite_url'] = invitation_url(token)
        return Response(data, status=status.HTTP_201_CREATED)


class InvitationRevokeView(APIView):
    """DELETE /api/access/invitations/<id>/ — revoca una invitación pendiente."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'DELETE': 'access.manage_users'}

    def delete(self, request, pk):
        services.revoke_invitation(generics.get_object_or_404(Invitation.objects, pk=pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


def _roles():
    return Role.objects.annotate(
        members_count=Count('memberships', filter=Q(memberships__status=Membership.Status.ACTIVE)),
    ).prefetch_related('permissions').order_by('-is_system', 'name')


class RoleListCreateView(APIView):
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'access.view', 'POST': 'access.manage_roles'}

    def get(self, request):
        return Response(RoleSerializer(_roles(), many=True).data)

    def post(self, request):
        serializer = RoleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data.get('name'):
            return Response({'name': ['Indica un nombre.']}, status=status.HTTP_400_BAD_REQUEST)
        role = services.create_role(actor=request.membership, name=serializer.validated_data['name'],
                                    permissions=serializer.validated_data.get('permissions', []))
        return Response(RoleSerializer(_roles().get(pk=role.pk)).data, status=status.HTTP_201_CREATED)


class RoleDetailView(APIView):
    permission_classes = [HasTenantPermission]
    required_permissions = {'PATCH': 'access.manage_roles', 'DELETE': 'access.manage_roles'}

    def patch(self, request, pk):
        serializer = RoleWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = services.update_role(actor=request.membership, role=generics.get_object_or_404(Role.objects, pk=pk),
                                    **serializer.validated_data)
        return Response(RoleSerializer(_roles().get(pk=role.pk)).data)

    def delete(self, request, pk):
        services.delete_role(generics.get_object_or_404(Role.objects, pk=pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


class PermissionCatalogView(APIView):
    """GET /api/access/permissions/ — catálogo de permisos, marcando los no incluidos en el plan."""
    permission_classes = [HasTenantPermission]
    required_permissions = {'GET': 'access.view'}

    def get(self, request):
        features = entitlements.for_tenant(request.membership.tenant_id).features
        return Response(PermissionSerializer(Permission.objects.all(), many=True,
                                             context={'features': features}).data)


# ── Endpoints públicos de invitación (/api/auth/...) ──────────────────────────

class InvitationPreviewView(APIView):
    """GET /api/auth/invitation/<token>/ — datos para la pantalla de aceptación."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def get(self, request, token):
        invitation = services.find_pending_invitation(token)
        if invitation is None:
            return Response({'detail': 'La invitación no es válida o ya expiró.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'email': invitation.email,
            'tenant_name': invitation.tenant.name,
            'role_name': invitation.role.name,
            'account_exists': get_user_model().objects.filter(email__iexact=invitation.email).exists(),
        })


class AcceptInvitationView(APIView):
    """POST /api/auth/accept-invitation/ — acepta y devuelve tokens para la empresa invitante."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, tenant_id = services.accept_invitation(**serializer.validated_data)
        bind_actor(user)
        audit.security_event(SecurityEvent.Kind.INVITATION_ACCEPTED, user=user, tenant_id=tenant_id)
        return Response(issue_tokens(user, tenant_id), status=status.HTTP_201_CREATED)
