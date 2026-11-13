from django.urls import path

from gestorpro.core.access.views import AcceptInvitationView, InvitationPreviewView

from .views import (
    ChangePasswordView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    MeView,
    MfaVerifyView,
    RefreshView,
    RegisterView,
    ResetPasswordView,
    SwitchTenantView,
)

# Endpoints de API con JWT en cabecera Authorization. La única cookie es la del
# refresh (httpOnly, SameSite=Strict, solo /api/auth/): refresh, logout y
# switch-tenant la leen; refresh además verifica el Origin (ver tokens.py).
urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('mfa/verify/', MfaVerifyView.as_view(), name='auth-mfa-verify'),
    path('token/refresh/', RefreshView.as_view(), name='auth-token-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('switch-tenant/', SwitchTenantView.as_view(), name='auth-switch-tenant'),
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('password/forgot/', ForgotPasswordView.as_view(), name='auth-password-forgot'),
    path('password/reset/<str:uid>/<str:token>/', ResetPasswordView.as_view(), name='auth-password-reset'),
    path('invitation/<str:token>/', InvitationPreviewView.as_view(), name='auth-invitation-preview'),
    path('accept-invitation/', AcceptInvitationView.as_view(), name='auth-accept-invitation'),
]
