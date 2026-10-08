"""
Catálogo del Core.

Estado actual (Fase 3): se conserva el modelo `Product` heredado, ya aislado por
empresa. En la Fase de inventario se evolucionará a `Item` con tipo (producto
terminado / materia prima / reventa / servicio), unidades de medida y costo
promedio, y `stock` dejará de ser un campo editable para derivarse del libro de
movimientos (ver docs/miga/02-arquitectura-multitenant.md).
"""
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from gestorpro.core.tenancy.db import AuthoredTenantModel, TenantModel


class Category(TenantModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')

    class Meta(TenantModel.Meta):
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'name'], name='category_unique_name_per_tenant',
                                    violation_error_message='Ya existe una categoría con este nombre.'),
        ]

    def __str__(self):
        return self.name


class Product(AuthoredTenantModel):

    class ProductType(models.TextChoices):
        PRODUCT = 'product', 'Producto'
        SERVICE = 'service', 'Servicio'

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)  # SKU interno, único por empresa
    description = models.TextField(blank=True, default='')
    product_type = models.CharField(max_length=10, choices=ProductType.choices, default=ProductType.PRODUCT)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    image = models.ImageField(upload_to='products/', null=True, blank=True)

    price = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('19.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
    )

    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    minimum_stock = models.IntegerField(default=5, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)

    class Meta(AuthoredTenantModel.Meta):
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['name', 'id']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'code'], name='product_unique_code_per_tenant',
                                    violation_error_message='Ya existe un producto con este código.'),
        ]
        indexes = [models.Index(fields=['tenant', 'is_active'])]

    def __str__(self):
        return f'{self.code} — {self.name}'

    @property
    def is_low_stock(self):
        return self.product_type == self.ProductType.PRODUCT and self.stock <= self.minimum_stock
