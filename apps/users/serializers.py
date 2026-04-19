from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer para registrar un nuevo usuario.
    Recibe los datos del frontend, los valida y crea el usuario.
    """
    password  = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label='Confirmar contraseña')

    class Meta:
        model  = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password2']

    def validate(self, data):
        # Validación personalizada: las dos contraseñas deben coincidir
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Las contraseñas no coinciden.'})
        return data

    def create(self, validated_data):
        # Quitamos password2 antes de crear el usuario (no es un campo del modelo)
        validated_data.pop('password2')
        # Usamos create_user para que la contraseña quede hasheada
        return User.objects.create_user(**validated_data)


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
