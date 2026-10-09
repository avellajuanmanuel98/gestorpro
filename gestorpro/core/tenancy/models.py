from django.db import models
from django.db.models import Q

from .db import TenantModel


class Tenant(models.Model):
    """
    Una empresa cliente de GestorPro. Todo dato de negocio cuelga de un Tenant.
    En la interfaz se llama "Empresa".
    """

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Activa'
        SUSPENDED = 'suspended', 'Suspendida'

    class Vertical(models.TextChoices):
        GENERIC = 'generic', 'GestorPro (general)'
        BAKERY = 'bakery', 'Miga (panaderías)'

    name = models.CharField(verbose_name='nombre', max_length=200)
    legal_name = models.CharField(verbose_name='razón social', max_length=200, blank=True, default='')
    slug = models.SlugField(unique=True)
    tax_id = models.CharField('NIT / identificación tributaria', max_length=30, blank=True, default='')
    vertical = models.CharField(
        verbose_name='vertical', max_length=20, choices=Vertical.choices, default=Vertical.GENERIC,
    )
    status = models.CharField(verbose_name='estado', max_length=20, choices=Status.choices, default=Status.ACTIVE)

    email = models.EmailField(verbose_name='email', blank=True, default='')
    phone = models.CharField(verbose_name='teléfono', max_length=30, blank=True, default='')
    address = models.TextField(verbose_name='dirección', blank=True, default='')
    city = models.CharField(verbose_name='ciudad', max_length=100, blank=True, default='')
    logo = models.ImageField(verbose_name='logo', upload_to='logos/', null=True, blank=True)

    timezone = models.CharField(verbose_name='zona horaria', max_length=64, default='America/Bogota')
    currency = models.CharField(verbose_name='moneda', max_length=3, default='COP')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE


class Location(TenantModel):
    """
    Sucursal / punto de venta. Existe desde el día 1 aunque la empresa tenga
    una sola sede: caja, inventario y ventas se registran por sucursal, y
    añadir esta dimensión después obligaría a migrar todos los documentos.
    """
    name = models.CharField(verbose_name='nombre', max_length=120)
    address = models.TextField(verbose_name='dirección', blank=True, default='')
    phone = models.CharField(verbose_name='teléfono', max_length=30, blank=True, default='')
    is_default = models.BooleanField(verbose_name='principal', default=False)
    is_active = models.BooleanField(verbose_name='activo', default=True)

    class Meta(TenantModel.Meta):
        verbose_name = 'Sucursal'
        verbose_name_plural = 'Sucursales'
        ordering = ['-is_default', 'name']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='location_unique_name_per_tenant'),
            models.UniqueConstraint(fields=['tenant'], condition=Q(is_default=True),
                                    name='location_single_default_per_tenant'),
        ]

    def __str__(self):
        return self.name
