from rest_framework import serializers

from .models import Location, Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'legal_name', 'slug', 'tax_id', 'vertical', 'status',
                  'email', 'phone', 'address', 'city', 'logo', 'timezone', 'currency', 'created_at']
        # Identidad, vertical y estado los administra la plataforma, no la empresa.
        read_only_fields = ['id', 'slug', 'vertical', 'status', 'timezone', 'currency', 'created_at']


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'address', 'phone', 'is_default', 'is_active']
