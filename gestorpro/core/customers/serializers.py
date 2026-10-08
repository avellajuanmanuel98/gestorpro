from rest_framework import serializers

from gestorpro.core.api.serializers import TenantModelSerializer

from .models import Customer


class CustomerSerializer(TenantModelSerializer):
    full_name = serializers.CharField(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'tenant', 'document_type', 'document_number',
            'first_name', 'last_name', 'full_name', 'company_name',
            'email', 'phone', 'address', 'city', 'status', 'notes',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class CustomerListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Customer
        fields = ['id', 'full_name', 'company_name', 'document_number', 'email', 'phone', 'city', 'status']
