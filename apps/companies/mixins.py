from rest_framework.exceptions import PermissionDenied


class CompanyFilterMixin:
    """
    Mixin que filtra automáticamente los querysets por la empresa
    del usuario autenticado.

    Cómo funciona:
    - Cada view que herede este mixin solo verá datos de su empresa
    - Si el usuario no tiene empresa asignada, lanza error 403
    - Se usa en TODAS las vistas que manejan datos sensibles

    Ejemplo de uso:
        class ClientListView(CompanyFilterMixin, generics.ListCreateAPIView):
            ...
    """

    def get_queryset(self):
        user = self.request.user

        if not user.company:
            raise PermissionDenied('Tu cuenta no está asociada a ninguna empresa.')

        # Llamamos al queryset del padre y filtramos por empresa
        queryset = super().get_queryset()
        return queryset.filter(company=user.company)

    def perform_create(self, serializer):
        """
        Al crear cualquier objeto, asignamos automáticamente
        la empresa y el usuario del request.
        No hace falta que el frontend envíe estos datos.
        """
        user = self.request.user
        if not user.company:
            raise PermissionDenied('Tu cuenta no está asociada a ninguna empresa.')

        kwargs = {'company': user.company}

        # Si el modelo tiene created_by, lo asignamos también
        import inspect
        sig = inspect.signature(serializer.save)
        kwargs['company'] = user.company

        # Verificamos si el serializer acepta created_by
        model_fields = [f.name for f in serializer.Meta.model._meta.get_fields()]
        if 'created_by' in model_fields:
            kwargs['created_by'] = user

        serializer.save(**kwargs)
