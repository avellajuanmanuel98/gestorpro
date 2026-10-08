from django.db import models
from django.db.models import Q

from gestorpro.core.tenancy.db import AuthoredTenantModel


class Supplier(AuthoredTenantModel):

    class DocumentType(models.TextChoices):
        NIT = 'NIT', 'NIT'
        CC = 'CC', 'Cédula de ciudadanía'
        CE = 'CE', 'Cédula de extranjería'
        PP = 'PP', 'Pasaporte'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Activo'
        INACTIVE = 'inactive', 'Inactivo'

    # Categorías genéricas; los verticales podrán aportar las suyas
    # (catálogo por empresa) cuando se implemente compras.
    class Category(models.TextChoices):
        MATERIALS = 'materials', 'Materiales e insumos'
        SERVICES = 'services', 'Servicios'
        TECHNOLOGY = 'technology', 'Tecnología'
        LOGISTICS = 'logistics', 'Logística y transporte'
        MARKETING = 'marketing', 'Marketing y publicidad'
        OTHER = 'other', 'Otro'

    company_name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=200, blank=True, default='')
    document_type = models.CharField(max_length=5, choices=DocumentType.choices, default=DocumentType.NIT)
    document_number = models.CharField(max_length=20, blank=True, default='')

    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    website = models.URLField(blank=True, default='')

    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True, default='')

    class Meta(AuthoredTenantModel.Meta):
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering = ['company_name', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'document_type', 'document_number'],
                condition=~Q(document_number=''),
                name='supplier_unique_document_per_tenant',
                violation_error_message='Ya existe un proveedor con este documento.',
            ),
        ]

    def __str__(self):
        return self.company_name
