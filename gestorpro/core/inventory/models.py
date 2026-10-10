"""
Libro de inventario: TODA variación de existencias es un movimiento.

    StockMovement   (inmutable)   ─ qué entró o salió, dónde, a qué costo y por qué
    StockLevel      (materializado) ─ existencia por ítem y sucursal

`Item.stock` es la suma de todas las sucursales y `Item.avg_cost` el costo
promedio ponderado de la empresa. Ambos se actualizan en la misma transacción
que el movimiento (ver services.post), así que siempre cuadran con el libro.
"""
from django.conf import settings
from django.db import models

from gestorpro.core.tenancy.db import TenantModel


class StockLevel(TenantModel):
    item = models.ForeignKey('catalog.Item', on_delete=models.CASCADE, related_name='stock_levels')
    location = models.ForeignKey('tenancy.Location', on_delete=models.PROTECT, related_name='+')
    quantity = models.DecimalField(max_digits=16, decimal_places=4, default=0)

    class Meta(TenantModel.Meta):
        verbose_name = 'Existencia por sucursal'
        constraints = [models.UniqueConstraint(fields=['item', 'location'], name='stock_level_unique')]


class StockMovement(TenantModel):

    class Type(models.TextChoices):
        OPENING = 'opening', 'Saldo inicial'
        PURCHASE = 'purchase', 'Compra'
        SALE = 'sale', 'Venta'
        SALE_VOID = 'sale_void', 'Anulación de venta'
        PRODUCTION_CONSUME = 'production_consume', 'Consumo en producción'
        PRODUCTION_OUTPUT = 'production_output', 'Producción'
        WASTE = 'waste', 'Merma'
        ADJUSTMENT_IN = 'adjustment_in', 'Ajuste (sobrante)'
        ADJUSTMENT_OUT = 'adjustment_out', 'Ajuste (faltante)'

    INBOUND = (Type.OPENING, Type.PURCHASE, Type.SALE_VOID, Type.PRODUCTION_OUTPUT, Type.ADJUSTMENT_IN)

    item = models.ForeignKey('catalog.Item', on_delete=models.PROTECT, related_name='movements')
    location = models.ForeignKey('tenancy.Location', on_delete=models.PROTECT, related_name='+')
    type = models.CharField(verbose_name='tipo', max_length=20, choices=Type.choices)
    quantity = models.DecimalField(verbose_name='cantidad', max_digits=16, decimal_places=4,
                                   help_text='Con signo, en la unidad del ítem: positivo entra, negativo sale.')
    unit_cost = models.DecimalField(verbose_name='costo unitario', max_digits=16, decimal_places=4)
    total_cost = models.DecimalField(verbose_name='costo total', max_digits=18, decimal_places=4)
    # Foto del ítem justo después del movimiento: el kardex se lee sin recalcular
    balance_after = models.DecimalField(max_digits=16, decimal_places=4)
    avg_cost_after = models.DecimalField(max_digits=16, decimal_places=4)
    # Documento que originó el movimiento (venta, compra, lote, merma, conteo…)
    source_type = models.CharField(max_length=30, blank=True, default='')
    source_id = models.PositiveBigIntegerField(null=True, blank=True)
    source_label = models.CharField(max_length=60, blank=True, default='')
    reason = models.CharField(verbose_name='motivo', max_length=200, blank=True, default='')
    # Null solo en movimientos generados por el sistema (migración del saldo inicial)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                   related_name='+')

    class Meta(TenantModel.Meta):
        verbose_name = 'Movimiento de inventario'
        verbose_name_plural = 'Movimientos de inventario'
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['tenant', 'item', 'created_at']),
                   models.Index(fields=['tenant', 'type', 'created_at']),
                   models.Index(fields=['tenant', 'source_type', 'source_id'])]
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(type__in=['opening', 'purchase', 'sale_void', 'production_output',
                                              'adjustment_in'], quantity__gt=0)
                           | models.Q(type__in=['sale', 'production_consume', 'waste', 'adjustment_out'],
                                      quantity__lt=0)),
                name='stock_movement_sign_matches_type'),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError('Los movimientos de inventario no se modifican; registra un ajuste.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Los movimientos de inventario no se borran.')
