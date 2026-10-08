from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Solo para el equipo de GestorPro (se crea a mano, nunca en un deploy)."""
        extra_fields.update(is_staff=True, is_superuser=True, is_platform_admin=True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Identidad global (una persona = una cuenta). NO pertenece a una empresa:
    el vínculo con empresas y el rol en cada una viven en access.Membership.
    """
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # acceso al admin de Django
    is_platform_admin = models.BooleanField(
        default=False, help_text='Personal de GestorPro: acceso al panel global, nunca a datos de una empresa.',
    )
    last_tenant = models.ForeignKey(
        'tenancy.Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
        help_text='Última empresa usada; se propone al iniciar sesión.',
    )
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f'{self.full_name} ({self.email})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()
