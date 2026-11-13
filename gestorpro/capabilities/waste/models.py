"""
Mermas: lo que se pierde (quemado, vencido, dañado, sobrante del día…).

Cada merma sale del libro de inventario al costo promedio vigente, así su
costo queda congelado y los reportes muestran cuánto dinero se perdió y por qué.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

from gestorpro.core.tenancy.db import TenantModel


class WasteReason(TenantModel):
    code = models.CharField(max_length=30)
    name = models.CharField(verbose_name='motivo', max_length=60)
    is_active = models.BooleanField(default=True)
    sort = models.PositiveSmallIntegerField(default=0)

    class Meta(TenantModel.Meta):
        verbose_name = 'Motivo de merma'
        ordering = ['sort', 'name']
        constraints = [models.UniqueConstraint(fields=['tenant', 'code'], name='waste_reason_unique_code')]

    def __str__(self):
        return self.name


class WasteRecord(TenantModel):
    location = models.ForeignKey('tenancy.Location', on_delete=models.PROTECT, related_name='+')
    item = models.ForeignKey('catalog.Item', on_delete=models.PROTECT, related_name='waste_records')
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    reason = models.ForeignKey(WasteReason, on_delete=models.PROTECT, related_name='records')
    unit_cost = models.DecimalField(max_digits=16, decimal_places=4)
    total_cost = models.DecimalField(max_digits=18, decimal_places=4)
    notes = models.CharField(max_length=200, blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')

    class Meta(TenantModel.Meta):
        verbose_name = 'Merma'
        verbose_name_plural = 'Mermas'
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['tenant', 'created_at'])]
        constraints = [models.CheckConstraint(condition=Q(quantity__gt=0), name='waste_quantity_positive')]
