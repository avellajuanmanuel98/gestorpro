from django.db import models
from django.db.models import Q

from gestorpro.core.tenancy.db import AuthoredTenantModel


class Customer(AuthoredTenantModel):
    """
    Cliente de una empresa (persona natural o jurídica).

    Documento y email son opcionales: en comercio de mostrador la mayoría de
    ventas son a "consumidor final". La unicidad del documento es POR EMPRESA:
    dos panaderías pueden tener al mismo cliente sin saberlo una de la otra.
    """

    class DocumentType(models.TextChoices):
        CC = 'CC', 'Cédula de ciudadanía'
        NIT = 'NIT', 'NIT'
        CE = 'CE', 'Cédula de extranjería'
        PP = 'PP', 'Pasaporte'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Activo'
        INACTIVE = 'inactive', 'Inactivo'

    document_type = models.CharField(max_length=5, choices=DocumentType.choices, default=DocumentType.CC)
    document_number = models.CharField(max_length=20, blank=True, default='')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True, default='')
    company_name = models.CharField(max_length=200, blank=True, default='')

    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True, default='')

    class Meta(AuthoredTenantModel.Meta):
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['first_name', 'last_name', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'document_type', 'document_number'],
                condition=~Q(document_number=''),
                name='customer_unique_document_per_tenant',
                violation_error_message='Ya existe un cliente con este documento.',
            ),
        ]
        indexes = [models.Index(fields=['tenant', 'status'])]

    def __str__(self):
        return f'{self.company_name} ({self.full_name})' if self.company_name else self.full_name

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()
