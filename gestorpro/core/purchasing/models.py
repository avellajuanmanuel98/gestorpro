"""
Compras: recepción de mercancía de un proveedor.

    PurchaseReceipt ─< PurchaseLine >─ Item

Cada línea se registra en la unidad en que se compró (bulto, arroba, kg…) y
el servicio la convierte a la unidad del ítem antes de entrar al libro de
inventario. Es lo que alimenta el costo promedio ponderado.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

from gestorpro.core.tenancy.db import TenantModel


class PurchaseReceipt(TenantModel):
    number = models.CharField(verbose_name='número', max_length=30)
    location = models.ForeignKey('tenancy.Location', on_delete=models.PROTECT, related_name='+')
    supplier = models.ForeignKey('suppliers.Supplier', verbose_name='proveedor', on_delete=models.PROTECT,
                                 null=True, blank=True, related_name='purchases')
    supplier_invoice = models.CharField(verbose_name='factura del proveedor', max_length=60, blank=True, default='')
    received_on = models.DateField(verbose_name='fecha de recepción')
    total = models.DecimalField(max_digits=16, decimal_places=2)
    notes = models.TextField(verbose_name='notas', blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')

    class Meta(TenantModel.Meta):
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        ordering = ['-received_on', '-id']
        constraints = [models.UniqueConstraint(fields=['tenant', 'location', 'number'],
                                               name='purchase_unique_number')]

    def __str__(self):
        return self.number


class PurchaseLine(TenantModel):
    receipt = models.ForeignKey(PurchaseReceipt, on_delete=models.CASCADE, related_name='lines')
    item = models.ForeignKey('catalog.Item', on_delete=models.PROTECT, related_name='purchase_lines')
    quantity = models.DecimalField(verbose_name='cantidad', max_digits=14, decimal_places=4)
    unit = models.ForeignKey('catalog.UnitOfMeasure', verbose_name='unidad', on_delete=models.PROTECT,
                             related_name='+')
    unit_cost = models.DecimalField(verbose_name='costo por unidad de compra', max_digits=14, decimal_places=4)
    total = models.DecimalField(max_digits=16, decimal_places=2)
    # En la unidad del ítem (lo que entra al inventario)
    base_quantity = models.DecimalField(max_digits=16, decimal_places=4)
    base_unit_cost = models.DecimalField(max_digits=16, decimal_places=4)

    class Meta(TenantModel.Meta):
        verbose_name = 'Línea de compra'
        ordering = ['id']
        constraints = [models.CheckConstraint(condition=Q(quantity__gt=0) & Q(unit_cost__gte=0),
                                              name='purchase_line_valid')]
