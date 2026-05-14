from rest_framework import serializers
from .models import Employee


class EmployeeSerializer(serializers.ModelSerializer):
    full_name  = serializers.CharField(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = Employee
        fields = [
            'id', 'document_type', 'document_number',
            'first_name', 'last_name', 'full_name',
            'email', 'phone', 'address', 'city',
            'position', 'department', 'hire_date', 'salary',
            'status', 'notes',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class EmployeeListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model  = Employee
        fields = [
            'id', 'full_name', 'email', 'phone',
            'position', 'department', 'hire_date', 'status',
        ]
