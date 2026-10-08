from django.contrib.auth import authenticate, password_validation
from django.db import transaction
from rest_framework import serializers

from gestorpro.core.access.services import provision_tenant

from .models import User


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'avatar', 'is_platform_admin', 'date_joined']
        read_only_fields = ['id', 'email', 'is_platform_admin', 'date_joined']


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(self.context['request'], email=attrs['email'].lower(), password=attrs['password'])
        if user is None or not user.is_active:
            raise serializers.ValidationError('Email o contraseña incorrectos.', code='invalid_credentials')
        attrs['user'] = user
        return attrs


class RegisterSerializer(serializers.Serializer):
    """Alta pública: crea usuario + empresa (el usuario queda como OWNER)."""
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password2 = serializers.CharField(write_only=True, trim_whitespace=False)
    company_name = serializers.CharField(max_length=200)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este email.')
        return value.lower()

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': 'Las contraseñas no coinciden.'})
        candidate = User(email=data['email'], first_name=data['first_name'], last_name=data['last_name'])
        password_validation.validate_password(data['password'], candidate)
        return data

    @transaction.atomic
    def create(self, validated):
        user = User.objects.create_user(
            email=validated['email'], password=validated['password'],
            first_name=validated['first_name'], last_name=validated['last_name'],
        )
        tenant = provision_tenant(name=validated['company_name'], owner=user)
        user.last_tenant = tenant
        user.save(update_fields=['last_tenant'])
        return user


class SwitchTenantSerializer(serializers.Serializer):
    tenant_id = serializers.IntegerField()
    refresh = serializers.CharField(required=False)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('La contraseña actual es incorrecta.')
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError({'new_password2': 'Las contraseñas no coinciden.'})
        password_validation.validate_password(data['new_password'], self.context['request'].user)
        return data
