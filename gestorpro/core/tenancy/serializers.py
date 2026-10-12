from rest_framework import serializers

from .models import Location, Tenant
from .modules import OPTIONAL_MODULES


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'legal_name', 'slug', 'tax_id', 'vertical', 'status', 'modules',
                  'email', 'phone', 'address', 'city', 'logo', 'timezone', 'currency', 'created_at']
        # Identidad, vertical y estado los administra la plataforma, no la empresa.
        read_only_fields = ['id', 'slug', 'vertical', 'status', 'timezone', 'currency', 'created_at']

    def validate_modules(self, value):
        if not isinstance(value, list) or any(not isinstance(k, str) for k in value):
            raise serializers.ValidationError('Debe ser una lista de módulos.')
        unknown = sorted(set(value) - set(OPTIONAL_MODULES))
        if unknown:
            raise serializers.ValidationError(f'Módulo desconocido: {", ".join(unknown)}.')
        return sorted(set(value))


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'address', 'phone', 'is_default', 'is_active']
