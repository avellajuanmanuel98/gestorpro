from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """
    Manager personalizado para crear usuarios y superusuarios.
    Django lo llama internamente cuando hacemos User.objects.create_user(...)
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)  # convierte a minúsculas
        user = self.model(email=email, **extra_fields)
        user.set_password(password)          # hashea la contraseña, nunca en texto plano
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Usuario personalizado del sistema.
    Usamos email como identificador en lugar de username
    porque es lo que usan la mayoría de sistemas modernos.
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        EMPLOYEE = 'employee', 'Empleado'

    # Datos principales
    email      = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name  = models.CharField(max_length=100)
    role       = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    avatar     = models.ImageField(upload_to='avatars/', null=True, blank=True)

    # Campos requeridos por Django
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    # Usamos email en vez de username para el login
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name        = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering            = ['first_name', 'last_name']

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.email})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN
