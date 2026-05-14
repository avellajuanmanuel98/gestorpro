from django.db import models
from django.conf import settings


class Employee(models.Model):

    class DocumentType(models.TextChoices):
        CC = 'CC', 'Cédula de ciudadanía'
        CE = 'CE', 'Cédula de extranjería'
        PP = 'PP', 'Pasaporte'

    class Status(models.TextChoices):
        ACTIVE   = 'active',   'Activo'
        INACTIVE = 'inactive', 'Inactivo'

    class Department(models.TextChoices):
        ADMIN      = 'admin',      'Administración'
        SALES      = 'sales',      'Ventas'
        OPERATIONS = 'operations', 'Operaciones'
        FINANCE    = 'finance',    'Finanzas'
        IT         = 'it',         'Tecnología'
        HR         = 'hr',         'Recursos Humanos'
        OTHER      = 'other',      'Otro'

    # ── Identificación ──────────────────────────────
    document_type   = models.CharField(max_length=5, choices=DocumentType.choices, default=DocumentType.CC)
    document_number = models.CharField(max_length=20)
    first_name      = models.CharField(max_length=100)
    last_name       = models.CharField(max_length=100)

    # ── Contacto ────────────────────────────────────
    email   = models.EmailField()
    phone   = models.CharField(max_length=20, blank=True, default='')
    address = models.TextField(blank=True, default='')
    city    = models.CharField(max_length=100, blank=True, default='')

    # ── Información laboral ──────────────────────────
    position   = models.CharField(max_length=100)
    department = models.CharField(max_length=20, choices=Department.choices, default=Department.OTHER)
    hire_date  = models.DateField()
    salary     = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # ── Estado ──────────────────────────────────────
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    notes  = models.TextField(blank=True, default='')

    # ── Multitenancy ────────────────────────────────
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='employees',
    )

    # ── Auditoría ───────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='employees_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Empleado'
        verbose_name_plural = 'Empleados'
        ordering            = ['first_name', 'last_name']
        unique_together     = [('company', 'document_number')]

    def __str__(self):
        return f'{self.full_name} — {self.position}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'
