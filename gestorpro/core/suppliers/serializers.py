from rest_framework import serializers

from gestorpro.core.api.serializers import TenantModelSerializer

from .models import Supplier


class SupplierSerializer(TenantModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Supplier
        fields = [
            'id', 'tenant', 'company_name', 'contact_name', 'document_type', 'document_number',
            'email', 'phone', 'address', 'city', 'website',
            'category', 'status', 'notes',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class SupplierListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'company_name', 'contact_name', 'email', 'phone', 'city', 'category', 'status']
