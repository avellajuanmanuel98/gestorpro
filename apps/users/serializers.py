from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.text import slugify
import uuid

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer para registrar un nuevo usuario.
    Al registrarse, se crea automáticamente una empresa
    y el usuario queda como Administrador de esa empresa.
    """
    password      = serializers.CharField(write_only=True, min_length=8)
    password2     = serializers.CharField(write_only=True, label='Confirmar contraseña')
    company_name  = serializers.CharField(max_length=200, write_only=True)

    class Meta:
        model  = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password2', 'company_name']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Las contraseñas no coinciden.'})
        return data

    def create(self, validated_data):
        from apps.companies.models import Company

        validated_data.pop('password2')
        company_name = validated_data.pop('company_name')

        # Creamos la empresa primero
        # El slug es un identificador URL-friendly: "Mi Empresa" -> "mi-empresa"
        base_slug = slugify(company_name)
        slug = base_slug
        # Si el slug ya existe, agregamos un sufijo único
        if Company.objects.filter(slug=slug).exists():
            slug = f'{base_slug}-{uuid.uuid4().hex[:6]}'

        company = Company.objects.create(name=company_name, slug=slug)

        # Creamos el usuario como Admin de esa empresa
        user = User.objects.create_user(
            company=company,
            role=User.Role.ADMIN,
            **validated_data
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para leer y actualizar el perfil del usuario.
    Nunca expone la contraseña.
    """
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'full_name', 'role', 'avatar', 'date_joined'
        ]
        # El email y la fecha no se pueden cambiar desde el perfil
        read_only_fields = ['id', 'email', 'role', 'date_joined']


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer para cambiar la contraseña del usuario autenticado.
    """
    current_password = serializers.CharField(write_only=True)
    new_password     = serializers.CharField(write_only=True, min_length=8)
    new_password2    = serializers.CharField(write_only=True, label='Confirmar nueva contraseña')

    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError({'new_password': 'Las contraseñas no coinciden.'})
        return data

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('La contraseña actual es incorrecta.')
        return value
