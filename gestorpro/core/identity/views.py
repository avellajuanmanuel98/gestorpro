from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from gestorpro.core import entitlements
from gestorpro.core.access.services import active_memberships_for
from gestorpro.core.audit import services as audit
from gestorpro.core.audit.context import bind_actor
from gestorpro.core.audit.models import SecurityEvent
from gestorpro.core.tenancy.context import tenant_context

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
    ent = entitlements.for_tenant(membership.tenant_id) if membership else entitlements.NONE
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
        # Plan: también solo para la UI; el backend valida funcionalidades y límites.
        'plan': None if membership is None else {
            'code': ent.plan_code, 'name': ent.plan_name, 'status': ent.status, 'trial_ends_at': ent.trial_ends_at,
        },
        'features': sorted(ent.features),
        'memberships': [
            {'tenant_id': m.tenant_id, 'tenant_name': m.tenant.name, 'role': m.role.name}
            for m in memberships
        ],
    }


def _audit_in_tenant(tenant_id, action, summary):
    if tenant_id is None:
        return
    with tenant_context(tenant_id):
        audit.record(action, summary=summary)


def _login_response(user, http_status=status.HTTP_200_OK, event=SecurityEvent.Kind.LOGIN_SUCCEEDED):
    tenant_id = choose_tenant(user, list(active_memberships_for(user)))
    if tenant_id is not None and user.last_tenant_id != tenant_id:
        user.last_tenant_id = tenant_id
        user.save(update_fields=['last_tenant'])
    bind_actor(user)
    audit.security_event(event, user=user, tenant_id=tenant_id)
    _audit_in_tenant(tenant_id, 'auth.login', f'{user.email} inició sesión')
    return Response(issue_tokens(user, tenant_id), status=http_status)


class LoginView(APIView):
    """POST /api/auth/login/ → {access, refresh}. El token apunta a la última empresa usada."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            audit.security_event(SecurityEvent.Kind.LOGIN_FAILED, email=str(request.data.get('email', '')))
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
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
        bind_actor(user)
        _audit_in_tenant(user.last_tenant_id, 'tenancy.tenant.created', f'{user.email} creó la empresa')
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
        audit.security_event(SecurityEvent.Kind.TENANT_SWITCHED, user=request.user, tenant_id=tenant_id)
        _audit_in_tenant(tenant_id, 'auth.tenant_switched', f'{request.user.email} entró a la empresa')
        return Response(issue_tokens(request.user, tenant_id))


class LogoutView(APIView):
    """POST /api/auth/logout/ → invalida el refresh token (no puede reutilizarse)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _blacklist(serializer.validated_data['refresh'], request.user)
        tenant_id = request.membership.tenant_id if request.membership else None
        audit.security_event(SecurityEvent.Kind.LOGOUT, user=request.user, tenant_id=tenant_id)
        audit.record('auth.logout', summary=f'{request.user.email} cerró sesión')
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
        audit.security_event(SecurityEvent.Kind.PASSWORD_CHANGED, user=request.user, tenant_id=tenant_id)
        audit.record('auth.password_changed', summary=f'{request.user.email} cambió su contraseña')
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
