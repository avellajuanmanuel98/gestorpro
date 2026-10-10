"""
Consecutivos de documentos (ventas, y más adelante compras, devoluciones…).

Un contador por empresa, sucursal y tipo de documento. Se bloquea con
SELECT … FOR UPDATE dentro de la transacción del documento: dos ventas
simultáneas nunca reciben el mismo número, y si la venta falla el número no
se consume (no quedan huecos). Preparado para la resolución de numeración de
la DIAN (prefijo y rango), que se configurará en la fase de facturación
electrónica.
"""
from django.db import models

from gestorpro.core.tenancy.db import TenantModel


class Sequence(TenantModel):
    location = models.ForeignKey('tenancy.Location', on_delete=models.CASCADE, related_name='+')
    doc_type = models.CharField(max_length=30)
    prefix = models.CharField(max_length=10, blank=True, default='')
    next_value = models.PositiveBigIntegerField(default=1)

    class Meta(TenantModel.Meta):
        verbose_name = 'Consecutivo'
        verbose_name_plural = 'Consecutivos'
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'location', 'doc_type'], name='sequence_unique_per_location'),
        ]

    def __str__(self):
        return f'{self.doc_type} {self.prefix}{self.next_value}'
