"""
Ventas de mostrador (POS).

    PaymentMethod                    (Efectivo, Tarjeta, Nequi, Daviplata, Transferencia)
    Sale ─< SaleLine >─ Item         (precio, IVA y costo congelados al vender)
         ─< Payment  >─ PaymentMethod

Reglas (ver services.py): todo se calcula en el servidor, la venta exige un
turno de caja abierto, nunca se borra (se anula, con motivo y permiso) y
cada venta recibe un consecutivo por sucursal sin huecos.

DIAN: `fiscal_status` deja preparado el documento equivalente electrónico.
Hoy toda venta queda "no reportada"; la integración con un proveedor
tecnológico autorizado es una fase propia, a validar con un contador.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

from gestorpro.core.tenancy.db import TenantModel


class PaymentMethod(TenantModel):

    class Kind(models.TextChoices):
        CASH = 'cash', 'Efectivo'
        CARD = 'card', 'Tarjeta'
        TRANSFER = 'transfer', 'Transferencia'
        WALLET = 'wallet', 'Billetera digital'

    code = models.CharField(max_length=30)
    name = models.CharField(verbose_name='nombre', max_length=60)
    kind = models.CharField(verbose_name='tipo', max_length=10, choices=Kind.choices)
    is_active = models.BooleanField(verbose_name='activo', default=True)
    sort = models.PositiveSmallIntegerField(default=0)

    class Meta(TenantModel.Meta):
        verbose_name = 'Medio de pago'
        verbose_name_plural = 'Medios de pago'
        ordering = ['sort', 'name']
        constraints = [models.UniqueConstraint(fields=['tenant', 'code'], name='payment_method_unique_code')]

    def __str__(self):
        return self.name

    @property
    def affects_cash_drawer(self) -> bool:
        """Solo el efectivo entra al cajón; los demás se concilian aparte."""
        return self.kind == self.Kind.CASH


class Sale(TenantModel):

    class Status(models.TextChoices):
        COMPLETED = 'completed', 'Completada'
        VOIDED = 'voided', 'Anulada'

    class FiscalStatus(models.TextChoices):
        NOT_REPORTED = 'not_reported', 'No reportada a la DIAN'

    number = models.CharField(verbose_name='número', max_length=30)
    location = models.ForeignKey('tenancy.Location', on_delete=models.PROTECT, related_name='+')
    cash_session = models.ForeignKey('cash.CashSession', on_delete=models.PROTECT, related_name='sales')
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='sales')
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    status = models.CharField(verbose_name='estado', max_length=10, choices=Status.choices,
                              default=Status.COMPLETED)
    # Clave que genera el POS por cada intento de cobro: un doble clic o un
    # reintento por mala conexión no crea dos ventas.
    client_uuid = models.UUIDField()

    subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    tax_total = models.DecimalField(verbose_name='impuestos', max_digits=14, decimal_places=2)
    discount = models.DecimalField(verbose_name='descuento', max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2)
    cost_total = models.DecimalField(verbose_name='costo', max_digits=16, decimal_places=4, default=0)
    change_given = models.DecimalField(verbose_name='cambio', max_digits=14, decimal_places=2, default=0)

    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name='+')
    void_reason = models.CharField(verbose_name='motivo de anulación', max_length=200, blank=True, default='')
    fiscal_status = models.CharField(max_length=20, choices=FiscalStatus.choices,
                                     default=FiscalStatus.NOT_REPORTED)

    class Meta(TenantModel.Meta):
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'location', 'number'], name='sale_unique_number'),
            models.UniqueConstraint(fields=['tenant', 'client_uuid'], name='sale_unique_client_uuid'),
            models.CheckConstraint(condition=Q(total__gte=0), name='sale_total_not_negative'),
        ]
        indexes = [models.Index(fields=['tenant', 'status', 'created_at']),
                   models.Index(fields=['tenant', 'cashier', 'created_at'])]

    def __str__(self):
        return self.number


class SaleLine(TenantModel):
    """Snapshot de lo vendido: si el precio o el costo cambian después, la venta no cambia."""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='lines')
    item = models.ForeignKey('catalog.Item', on_delete=models.PROTECT, related_name='sale_lines')
    item_name = models.CharField(max_length=200)
    unit_symbol = models.CharField(max_length=12)
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    line_subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=4)

    class Meta(TenantModel.Meta):
        verbose_name = 'Línea de venta'
        ordering = ['id']
        constraints = [models.CheckConstraint(condition=Q(quantity__gt=0), name='sale_line_quantity_positive')]


class Payment(TenantModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments')
    method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, related_name='+')
    amount = models.DecimalField(verbose_name='valor aplicado', max_digits=14, decimal_places=2)
    tendered = models.DecimalField(verbose_name='recibido', max_digits=14, decimal_places=2)
    reference = models.CharField(verbose_name='referencia', max_length=60, blank=True, default='')

    class Meta(TenantModel.Meta):
        verbose_name = 'Pago'
        ordering = ['id']
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0) & Q(tendered__gte=models.F('amount')),
                                              name='payment_amounts_valid')]
