from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from apps.companies.mixins import CompanyFilterMixin

from .models import Client
from .serializers import ClientSerializer, ClientListSerializer


class ClientListCreateView(CompanyFilterMixin, generics.ListCreateAPIView):
    """
    GET  /api/clients/  → lista clientes de la empresa del usuario
    POST /api/clients/  → crea un cliente en la empresa del usuario
    """
    queryset           = Client.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['first_name', 'last_name', 'email', 'company_name', 'document_number']
    ordering_fields    = ['first_name', 'created_at']
    ordering           = ['first_name']

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ClientListSerializer
        return ClientSerializer


class ClientDetailView(CompanyFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/DELETE /api/clients/{id}/
    Solo permite acceder a clientes de la propia empresa.
    """
    queryset           = Client.objects.all()
    serializer_class   = ClientSerializer
    permission_classes = [IsAuthenticated]
