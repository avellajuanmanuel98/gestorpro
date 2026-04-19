from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated

from .models import Client
from .serializers import ClientSerializer, ClientListSerializer


class ClientListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/clients/       → lista todos los clientes (paginado)
    POST /api/clients/       → crea un nuevo cliente

    Soporta búsqueda: /api/clients/?search=juan
    Soporta filtro:   /api/clients/?status=active
    """
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['first_name', 'last_name', 'email', 'company_name', 'document_number']
    ordering_fields    = ['first_name', 'created_at']
    ordering           = ['first_name']

    def get_queryset(self):
        queryset = Client.objects.all()
        # Filtro opcional por estado: ?status=active
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_serializer_class(self):
        # En el listado usamos el serializer reducido, en creación el completo
        if self.request.method == 'GET':
            return ClientListSerializer
        return ClientSerializer

    def perform_create(self, serializer):
        # Guardamos automáticamente quién creó el cliente
        serializer.save(created_by=self.request.user)


class ClientDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/clients/{id}/  → ver detalle de un cliente
    PUT    /api/clients/{id}/  → actualizar cliente
    DELETE /api/clients/{id}/  → eliminar cliente
    """
    queryset           = Client.objects.all()
    serializer_class   = ClientSerializer
    permission_classes = [IsAuthenticated]
