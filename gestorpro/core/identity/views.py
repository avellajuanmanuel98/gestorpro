from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from gestorpro.core.access.services import active_memberships_for

from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    SwitchTenantSerializer,
    UserSerializer,
)
from .tokens import choose_tenant, issue_tokens


def build_session(user, membership):
    """Estado de sesión que necesita el frontend para pintar la app."""
    memberships = list(active_memberships_for(user))
    return {
        'user': UserSerializer(user).data,
        'tenant': None if membership is None else {
            'id': membership.tenant.id,
            'name': membership.tenant.name,
            'slug': membership.tenant.slug,
            'vertical': membership.tenant.vertical,
        },
        'role': None if membership is None else {'code': membership.role.code, 'name': membership.role.name},
        # Solo para adaptar la UI: el backend vuelve a validar cada permiso.
        'permissions': [] if membership is None else sorted(membership.permission_codes),
        'memberships': [
            {'tenant_id': m.tenant_id, 'tenant_name': m.tenant.name, 'role': m.role.name}
            for m in memberships
        ],
    }


def _login_response(user, http_status=status.HTTP_200_OK):
    tenant_id = choose_tenant(user, list(active_memberships_for(user)))
    if tenant_id is not None and user.last_tenant_id != tenant_id:
        user.last_tenant_id = tenant_id
        user.save(update_fields=['last_tenant'])
    return Response(issue_tokens(user, tenant_id), status=http_status)


class LoginView(APIView):
    """POST /api/auth/login/ → {access, refresh}. El token apunta a la última empresa usada."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return _login_response(serializer.validated_data['user'])


class RegisterView(APIView):
    """POST /api/auth/register/ → crea cuenta + empresa y devuelve tokens."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return _login_response(user, status.HTTP_201_CREATED)


class MeView(APIView):
    """GET/PATCH /api/auth/me/ → sesión actual (usuario, empresa activa, rol, permisos)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build_session(request.user, request.membership))

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(build_session(request.user, request.membership))


class SwitchTenantView(APIView):
    """POST /api/auth/switch-tenant/ → nuevos tokens para otra empresa del usuario."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SwitchTenantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant_id = serializer.validated_data['tenant_id']
        if not active_memberships_for(request.user).filter(tenant_id=tenant_id).exists():
            return Response({'detail': 'No perteneces a esa empresa.'}, status=status.HTTP_403_FORBIDDEN)
        _blacklist(serializer.validated_data.get('refresh'), request.user)
        request.user.last_tenant_id = tenant_id
        request.user.save(update_fields=['last_tenant'])
        return Response(issue_tokens(request.user, tenant_id))


class LogoutView(APIView):
    """POST /api/auth/logout/ → invalida el refresh token (no puede reutilizarse)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _blacklist(serializer.validated_data['refresh'], request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    """POST /api/auth/change-password/ → cambia la contraseña y cierra las demás sesiones."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        for token in OutstandingToken.objects.filter(user=request.user):
            BlacklistedToken.objects.get_or_create(token=token)
        tenant_id = request.membership.tenant_id if request.membership else None
        return Response(issue_tokens(request.user, tenant_id))


def _blacklist(raw_refresh, user):
    if not raw_refresh:
        return
    try:
        token = RefreshToken(raw_refresh)
    except TokenError:
        return  # ya inválido/expirado: nada que revocar
    if str(token.get('user_id')) == str(user.pk):
        token.blacklist()
