from django.db import models
from django.conf import settings


class Client(models.Model):
    """
    Representa un cliente de la empresa que usa GestorPro.

    Guardamos tanto personas naturales como empresas,
    por eso tenemos 'company_name' como campo opcional.
    """

    class DocumentType(models.TextChoices):
        CC  = 'CC',  'Cédula de ciudadanía'
        NIT = 'NIT', 'NIT'
        CE  = 'CE',  'Cédula de extranjería'
        PP  = 'PP',  'Pasaporte'

    class Status(models.TextChoices):
        ACTIVE   = 'active',   'Activo'
        INACTIVE = 'inactive', 'Inactivo'

    # ── Identificación ──────────────────────────────
    document_type   = models.CharField(max_length=5, choices=DocumentType.choices, default=DocumentType.CC)
    document_number = models.CharField(max_length=20, unique=True)
    first_name      = models.CharField(max_length=100)
    last_name       = models.CharField(max_length=100)
    company_name    = models.CharField(max_length=200, blank=True, default='')

    # ── Contacto ────────────────────────────────────
    email   = models.EmailField(unique=True)
    phone   = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    city    = models.CharField(max_length=100, blank=True, default='')

    # ── Estado y notas ──────────────────────────────
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    notes  = models.TextField(blank=True, default='')

    # ── Multitenancy ─────────────────────────────────
    # Cada cliente pertenece a una empresa específica
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='clients'
    )

    # ── Auditoría ────────────────────────────────────
    # created_by guarda quién creó este cliente
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='clients_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering            = ['first_name', 'last_name']

    def __str__(self):
        if self.company_name:
            return f'{self.company_name} ({self.full_name})'
        return self.full_name

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'
