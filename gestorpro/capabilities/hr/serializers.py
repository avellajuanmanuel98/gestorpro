from rest_framework import serializers

from gestorpro.core.api.serializers import TenantModelSerializer

from .models import Employee


class SalaryVisibilityMixin:
    """El salario solo se lee o escribe con el permiso `hr.view_salary`."""

    def _can_see_salary(self):
        request = self.context.get('request')
        membership = getattr(request, 'membership', None)
        return bool(membership and membership.has_perm('hr.view_salary'))

    def get_fields(self):
        fields = super().get_fields()
        if not self._can_see_salary():
            fields.pop('salary', None)
        return fields


class EmployeeSerializer(SalaryVisibilityMixin, TenantModelSerializer):
    full_name = serializers.CharField(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'tenant', 'document_type', 'document_number',
            'first_name', 'last_name', 'full_name',
            'email', 'phone', 'address', 'city',
            'position', 'department', 'hire_date', 'salary',
            'status', 'notes', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class EmployeeListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Employee
        fields = ['id', 'full_name', 'email', 'phone', 'position', 'department', 'hire_date', 'status']
