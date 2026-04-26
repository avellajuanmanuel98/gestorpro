from django.db import models


class Company(models.Model):
    """
    Representa una empresa que usa GestorPro.

    En un SaaS multitenancy cada 'tenant' es una empresa.
    Todos los datos del sistema (clientes, facturas, productos)
    pertenecen a una empresa específica.
    """

    class Plan(models.TextChoices):
        FREE    = 'free',    'Gratis'
        STARTER = 'starter', 'Starter'
        PRO     = 'pro',     'Pro'

    name     = models.CharField(max_length=200)
    slug     = models.SlugField(unique=True)  # identificador único en URL: mi-empresa
    logo     = models.ImageField(upload_to='logos/', null=True, blank=True)
    plan     = models.CharField(max_length=10, choices=Plan.choices, default=Plan.FREE)

    # Datos de contacto de la empresa
    email    = models.EmailField(blank=True, default='')
    phone    = models.CharField(max_length=20, blank=True, default='')
    address  = models.TextField(blank=True, default='')
    city     = models.CharField(max_length=100, blank=True, default='')
    nit      = models.CharField(max_length=20, blank=True, default='')

    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering            = ['name']

    def __str__(self):
        return self.name
