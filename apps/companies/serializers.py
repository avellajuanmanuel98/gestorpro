from rest_framework import serializers
from .models import Company


class CompanySerializer(serializers.ModelSerializer):
    """
    Serializer completo de la empresa.
    Se usa para ver y editar los datos de la propia empresa.
    Los campos slug y plan solo los puede cambiar un superadmin,
    por eso los marcamos como read_only aquí.
    """
    class Meta:
        model  = Company
        fields = [
            'id', 'name', 'slug', 'plan',
            'email', 'phone', 'address', 'city', 'nit',
            'logo', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'slug', 'plan', 'is_active', 'created_at']
