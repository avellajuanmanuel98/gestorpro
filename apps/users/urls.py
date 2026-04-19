from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegisterView, ProfileView, ChangePasswordView

urlpatterns = [
    # Registro de nuevo usuario
    path('register/', RegisterView.as_view(), name='auth-register'),

    # Login — recibe email+password y devuelve access+refresh token
    path('login/', TokenObtainPairView.as_view(), name='auth-login'),

    # Renovar el access token usando el refresh token
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),

    # Perfil del usuario autenticado
    path('profile/', ProfileView.as_view(), name='auth-profile'),

    # Cambiar contraseña
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
]
