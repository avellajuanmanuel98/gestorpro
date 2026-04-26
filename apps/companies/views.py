from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from .models import Company
from .serializers import CompanySerializer


class MyCompanyView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/companies/me/  → devuelve los datos de la empresa del usuario
    PUT   /api/companies/me/  → actualiza los datos (solo rol admin)
    PATCH /api/companies/me/  → actualización parcial (solo rol admin)

    Un usuario solo puede ver y editar SU propia empresa.
    No hay forma de acceder a datos de otra empresa desde aquí.
    """
    serializer_class   = CompanySerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user

        # El usuario debe tener empresa asignada
        if not user.company:
            raise PermissionDenied('Tu cuenta no está asociada a ninguna empresa.')

        # Solo admins pueden modificar — empleados solo pueden leer
        if self.request.method not in ('GET', 'HEAD', 'OPTIONS'):
            if user.role != 'admin':
                raise PermissionDenied('Solo los administradores pueden editar la empresa.')

        return user.company
