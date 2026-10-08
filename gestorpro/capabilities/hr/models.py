from django.db import models

from gestorpro.core.tenancy.db import AuthoredTenantModel


class Employee(AuthoredTenantModel):
    """Ficha de personal (capability opcional; no es lo mismo que un usuario del sistema)."""

    class DocumentType(models.TextChoices):
        CC = 'CC', 'Cédula de ciudadanía'
        CE = 'CE', 'Cédula de extranjería'
        PP = 'PP', 'Pasaporte'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Activo'
        INACTIVE = 'inactive', 'Inactivo'

    class Department(models.TextChoices):
        ADMIN = 'admin', 'Administración'
        SALES = 'sales', 'Ventas'
        OPERATIONS = 'operations', 'Operaciones'
        FINANCE = 'finance', 'Finanzas'
        IT = 'it', 'Tecnología'
        HR = 'hr', 'Recursos Humanos'
        OTHER = 'other', 'Otro'

    document_type = models.CharField(max_length=5, choices=DocumentType.choices, default=DocumentType.CC)
    document_number = models.CharField(max_length=20)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')

    position = models.CharField(max_length=100)
    department = models.CharField(max_length=20, choices=Department.choices, default=Department.OTHER)
    hire_date = models.DateField()
    salary = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True, default='')

    class Meta(AuthoredTenantModel.Meta):
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'
        ordering = ['first_name', 'last_name', 'id']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'document_type', 'document_number'],
                                    name='employee_unique_document_per_tenant',
                                    violation_error_message='Ya existe un empleado con este documento.'),
        ]

    def __str__(self):
        return f'{self.full_name} — {self.position}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'
