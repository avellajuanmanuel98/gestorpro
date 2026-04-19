from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model

from .serializers import RegisterSerializer, UserSerializer, ChangePasswordSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Crea un nuevo usuario. No requiere autenticación.
    """
    serializer_class   = RegisterSerializer
    permission_classes = [AllowAny]  # este endpoint es público

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'message': 'Usuario creado exitosamente.',
                'user': UserSerializer(user).data
            },
            status=status.HTTP_201_CREATED
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/auth/profile/  → ver mi perfil
    PUT  /api/auth/profile/  → actualizar mi perfil
    Requiere estar autenticado (token JWT en el header).
    """
    serializer_class   = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Siempre devuelve el usuario que hace la petición
        return self.request.user


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Cambia la contraseña del usuario autenticado.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # set_password() hashea la contraseña antes de guardarla
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        return Response({'message': 'Contraseña actualizada exitosamente.'})
