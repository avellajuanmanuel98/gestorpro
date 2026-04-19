from rest_framework import serializers
from .models import Client


class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer principal del cliente.
    Maneja tanto lectura como escritura.
    """
    full_name   = serializers.CharField(read_only=True)
    created_by  = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = Client
        fields = [
            'id', 'document_type', 'document_number',
            'first_name', 'last_name', 'full_name', 'company_name',
            'email', 'phone', 'address', 'city',
            'status', 'notes',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class ClientListSerializer(serializers.ModelSerializer):
    """
    Versión reducida para el listado — menos campos = respuesta más rápida.
    Cuando tienes 500 clientes no necesitas traer las notas de cada uno.
    """
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model  = Client
        fields = [
            'id', 'full_name', 'company_name',
            'email', 'phone', 'city', 'status',
        ]
