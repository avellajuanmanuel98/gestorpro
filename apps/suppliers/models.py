from django.db import models
from django.conf import settings


class Supplier(models.Model):

    class DocumentType(models.TextChoices):
        NIT = 'NIT', 'NIT'
        CC  = 'CC',  'Cédula de ciudadanía'
        CE  = 'CE',  'Cédula de extranjería'
        PP  = 'PP',  'Pasaporte'

    class Status(models.TextChoices):
        ACTIVE   = 'active',   'Activo'
        INACTIVE = 'inactive', 'Inactivo'

    class Category(models.TextChoices):
        MATERIALS  = 'materials',  'Materiales e insumos'
        SERVICES   = 'services',   'Servicios'
        TECHNOLOGY = 'technology', 'Tecnología'
        LOGISTICS  = 'logistics',  'Logística y transporte'
        MARKETING  = 'marketing',  'Marketing y publicidad'
        OTHER      = 'other',      'Otro'

    # ── Identificación ──────────────────────────────
    company_name    = models.CharField(max_length=200)
    contact_name    = models.CharField(max_length=200, blank=True, default='')
    document_type   = models.CharField(max_length=5, choices=DocumentType.choices, default=DocumentType.NIT)
    document_number = models.CharField(max_length=20, blank=True, default='')

    # ── Contacto ────────────────────────────────────
    email   = models.EmailField(blank=True, default='')
    phone   = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    city    = models.CharField(max_length=100, blank=True, default='')
    website = models.URLField(blank=True, default='')

    # ── Clasificación ────────────────────────────────
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    status   = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    notes    = models.TextField(blank=True, default='')

    # ── Multitenancy ────────────────────────────────
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='suppliers',
    )

    # ── Auditoría ───────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='suppliers_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        ordering            = ['company_name']

    def __str__(self):
        return self.company_name
