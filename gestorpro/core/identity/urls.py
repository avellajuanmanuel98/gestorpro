from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import ChangePasswordView, LoginView, LogoutView, MeView, RegisterView, SwitchTenantView

# Endpoints de API con JWT en cabecera Authorization: no usan cookies de sesión,
# por lo que no aplican CSRF (DRF solo aplica CSRF a SessionAuthentication).
urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
    path('me/', MeView.as_view(), name='auth-me'),
    path('switch-tenant/', SwitchTenantView.as_view(), name='auth-switch-tenant'),
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
]
