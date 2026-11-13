from django.contrib.auth.models import update_last_login
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from gestorpro.core import entitlements
from gestorpro.core.access.services import active_membership_in, active_memberships_for
from gestorpro.core.audit import services as audit
from gestorpro.core.audit.context import bind_actor
from gestorpro.core.audit.models import SecurityEvent
from gestorpro.core.tenancy.context import tenant_context

from . import lockout, mfa
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    SwitchTenantSerializer,
    UserSerializer,
)
from .tokens import choose_tenant, clear_refresh_cookie, refresh_from, same_origin, set_refresh_cookie, token_response


def build_session(user, membership):
    """Estado de sesión que necesita el frontend para pintar la app."""
    memberships = active_memberships_for(user)
    ent = entitlements.for_tenant(membership.tenant_id) if membership else entitlements.NONE
    return {
        'user': UserSerializer(user).data,
        'tenant': None if membership is None else {
            'id': membership.tenant.id,
            'name': membership.tenant.name,
            'slug': membership.tenant.slug,
            'vertical': membership.tenant.vertical,
            'modules': sorted(membership.tenant.modules or []),
        },
        'role': None if membership is None else {'code': membership.role.code, 'name': membership.role.name},
        # Solo para adaptar la UI: el backend vuelve a validar cada permiso.
        'permissions': [] if membership is None else sorted(membership.permission_codes),
        # Plan: también solo para la UI; el backend valida funcionalidades y límites.
        'plan': None if membership is None else {
            'code': ent.plan_code, 'name': ent.plan_name, 'status': ent.status, 'trial_ends_at': ent.trial_ends_at,
        },
        'features': sorted(ent.features),
        # Sesión de soporte de la plataforma (solo lectura): la UI muestra un aviso permanente
        'support': None if not getattr(membership, 'is_support', False) else {
            'session': membership.session.id, 'reason': membership.session.reason,
            'expires_at': membership.session.expires_at.isoformat(), 'agent': user.email,
        },
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
    tenant_id = choose_tenant(user, active_memberships_for(user))
    if tenant_id is not None and user.last_tenant_id != tenant_id:
        user.last_tenant_id = tenant_id
        user.save(update_fields=['last_tenant'])
    update_last_login(None, user)
    bind_actor(user)
    audit.security_event(event, user=user, tenant_id=tenant_id)
    _audit_in_tenant(tenant_id, 'auth.login', f'{user.email} inició sesión')
    return token_response(user, tenant_id, http_status)


class LoginView(APIView):
    """POST /api/auth/login/ → {access, refresh}. El token apunta a la última empresa usada."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        email = lockout.normalize(request.data.get('email', ''))
        if lockout.is_locked(email):  # ni siquiera se verifica la contraseña
            audit.security_event(SecurityEvent.Kind.LOGIN_LOCKED, email=email)
            return Response({'detail': f'Demasiados intentos fallidos con este correo. Espera '
                                       f'{lockout.window().seconds // 60} minutos o usa "¿Olvidaste tu contraseña?".'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            audit.security_event(SecurityEvent.Kind.LOGIN_FAILED, email=email)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.validated_data['user']
        if mfa.required_for(user):  # personal de la plataforma: falta el código de su app
            pending = mfa.challenge(user)
            if pending is None:
                return Response({'detail': 'Tu cuenta de plataforma necesita verificación en dos pasos. Quien '
                                           'administra el servidor debe ejecutar: manage.py platform_admin '
                                           f'{user.email}', 'code': 'mfa_not_enrolled'},
                                status=status.HTTP_403_FORBIDDEN)
            return Response(pending)
        return _login_response(user)


class MfaVerifyView(APIView):
    """POST /api/auth/mfa/verify/ {mfa_token, code} → tokens, si el código de la app autenticadora es válido."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        user = mfa.user_from_token(request.data.get('mfa_token'))
        if user is None:
            return Response({'detail': 'La verificación venció. Vuelve a escribir tu contraseña.',
                             'code': 'mfa_expired'}, status=status.HTTP_400_BAD_REQUEST)
        if lockout.is_locked(user.email):
            audit.security_event(SecurityEvent.Kind.LOGIN_LOCKED, user=user)
            return Response({'detail': 'Demasiados intentos fallidos. Espera unos minutos.'},
                            status=status.HTTP_429_TOO_MANY_REQUESTS)
        with transaction.atomic():  # dos envíos simultáneos del mismo código: solo uno pasa
            user = type(user).objects.select_for_update().get(pk=user.pk)
            first_time = user.totp_confirmed_at is None
            accepted = mfa.verify(user, str(request.data.get('code', '')))
        if not accepted:
            audit.security_event(SecurityEvent.Kind.MFA_FAILED, user=user)
            return Response({'code': ['Código incorrecto o ya usado. Escribe el que muestra tu app ahora.']},
                            status=status.HTTP_400_BAD_REQUEST)
        if first_time:
            audit.security_event(SecurityEvent.Kind.MFA_ENROLLED, user=user)
        return _login_response(user)


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
        if active_membership_in(request.user, tenant_id) is None:
            return Response({'detail': 'No perteneces a esa empresa.'}, status=status.HTTP_403_FORBIDDEN)
        _blacklist(refresh_from(request), request.user)
        request.user.last_tenant_id = tenant_id
        request.user.save(update_fields=['last_tenant'])
        audit.security_event(SecurityEvent.Kind.TENANT_SWITCHED, user=request.user, tenant_id=tenant_id)
        _audit_in_tenant(tenant_id, 'auth.tenant_switched', f'{request.user.email} entró a la empresa')
        return token_response(request.user, tenant_id)


class LogoutView(APIView):
    """POST /api/auth/logout/ → revoca el refresh token de la cookie (no puede reutilizarse) y la borra."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _blacklist(refresh_from(request), request.user)
        tenant_id = request.membership.tenant_id if request.membership else None
        audit.security_event(SecurityEvent.Kind.LOGOUT, user=request.user, tenant_id=tenant_id)
        audit.record('auth.logout', summary=f'{request.user.email} cerró sesión')
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response


class RefreshView(APIView):
    """
    POST /api/auth/token/refresh/ → access nuevo. El refresh llega SOLO por la
    cookie httpOnly; rota en cada uso (el anterior queda revocado).
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'refresh'

    def post(self, request):
        if not same_origin(request):
            return Response({'detail': 'Origen no permitido.'}, status=status.HTTP_403_FORBIDDEN)
        raw = refresh_from(request)
        serializer = TokenRefreshSerializer(data={'refresh': raw or ''})
        try:
            if not raw:
                raise InvalidToken('Sin sesión.')
            serializer.is_valid(raise_exception=True)
        except (TokenError, InvalidToken, ValidationError):
            response = Response({'detail': 'La sesión venció. Vuelve a entrar.', 'code': 'session_expired'},
                                status=status.HTTP_401_UNAUTHORIZED)
            clear_refresh_cookie(response)
            return response
        data = serializer.validated_data
        response = Response({'access': data['access']})
        if data.get('refresh'):
            set_refresh_cookie(response, data['refresh'])
        return response


class ChangePasswordView(APIView):
    """POST /api/auth/change-password/ → cambia la contraseña y cierra las demás sesiones."""
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'sensitive'  # con una sesión robada no se puede probar la contraseña actual sin límite

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
        return token_response(request.user, tenant_id)


def _blacklist(raw_refresh, user):
    if not raw_refresh:
        return
    try:
        token = RefreshToken(raw_refresh)
    except TokenError:
        return  # ya inválido/expirado: nada que revocar
    if str(token.get('user_id')) == str(user.pk):
        token.blacklist()


class ForgotPasswordView(APIView):
    """POST /api/auth/password/forgot/ {email} → siempre 200 (no revela si la cuenta existe)."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        from django.conf import settings

        from . import password_reset
        email = str(request.data.get('email', '')).strip()[:254]
        if '@' not in email:
            return Response({'email': ['Escribe tu correo.']}, status=status.HTTP_400_BAD_REQUEST)
        password_reset.request_by_email(email)
        return Response({'email_enabled': bool(getattr(settings, 'EMAIL_ENABLED', False))})


class ResetPasswordView(APIView):
    """
    GET  /api/auth/password/reset/<uid>/<token>/ → {valid, email (enmascarado)}
    POST /api/auth/password/reset/<uid>/<token>/ {password, password2} → contraseña nueva
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def get(self, request, uid, token):
        from . import password_reset
        user = password_reset.user_from(uid, token)
        return Response({'valid': user is not None, 'email': password_reset.mask(user.email) if user else None})

    def post(self, request, uid, token):
        from . import password_reset
        user = password_reset.user_from(uid, token)
        if user is None:
            return Response({'detail': 'El enlace venció o ya se usó. Pide uno nuevo.'},
                            status=status.HTTP_400_BAD_REQUEST)
        password_reset.reset(user, str(request.data.get('password', '')), str(request.data.get('password2', '')))
        return Response({'ok': True})
