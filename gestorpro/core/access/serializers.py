from django.conf import settings
from rest_framework import serializers

from gestorpro.core import entitlements

from .models import Invitation, Membership, Permission, Role


class RoleSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'code', 'name']


class MemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    last_login = serializers.DateTimeField(source='user.last_login', read_only=True)
    role = RoleSummarySerializer(read_only=True)
    is_owner = serializers.BooleanField(source='role.grants_all', read_only=True)

    class Meta:
        model = Membership
        fields = ['id', 'email', 'full_name', 'role', 'is_owner', 'status', 'last_login', 'created_at']


class MemberUpdateSerializer(serializers.Serializer):
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects, required=False)  # filtrado por tenant
    status = serializers.ChoiceField(choices=[Membership.Status.ACTIVE, Membership.Status.SUSPENDED], required=False)


class InvitationSerializer(serializers.ModelSerializer):
    role = RoleSummarySerializer(read_only=True)
    status = serializers.CharField(read_only=True)
    invited_by = serializers.EmailField(source='invited_by.email', read_only=True, default=None)

    class Meta:
        model = Invitation
        fields = ['id', 'email', 'role', 'status', 'expires_at', 'invited_by', 'created_at']


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects)  # filtrado por tenant


def invitation_url(token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/invitation/{token}"


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    members_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Role
        fields = ['id', 'code', 'name', 'is_system', 'grants_all', 'permissions', 'members_count']

    def get_permissions(self, role):
        if role.grants_all:
            return ['*']
        return sorted(p.code for p in role.permissions.all())


class RoleWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80, required=False)
    permissions = serializers.ListField(child=serializers.CharField(max_length=80), required=False)


class PermissionSerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ['code', 'module', 'description', 'available']

    def get_available(self, permission):
        """False si el módulo no está incluido en el plan de la empresa."""
        feature = entitlements.MODULE_FEATURES.get(permission.module)
        return feature is None or feature in self.context['features']


class InvitationPreviewSerializer(serializers.Serializer):
    email = serializers.EmailField()
    tenant_name = serializers.CharField()
    role_name = serializers.CharField()
    account_exists = serializers.BooleanField()


class AcceptInvitationSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
