"""
Facturación a crédito y cotizaciones (cuentas por cobrar).

No es el POS: el POS de mostrador (ventas, pagos, caja) es un módulo propio.
Este módulo cubre documentos B2B con fecha de vencimiento.

Preparado para facturación electrónica (fase posterior, a validar con un
asesor tributario): número único por empresa, snapshots de precio/impuesto
por línea y totales persistidos e inmutables una vez emitida.
"""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from gestorpro.core.tenancy.db import AuthoredTenantModel, TenantModel


class Invoice(AuthoredTenantModel):

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Borrador'
        SENT = 'sent', 'Enviada'
        PAID = 'paid', 'Pagada'
        OVERDUE = 'overdue', 'Vencida'
        CANCELLED = 'cancelled', 'Cancelada'

    class InvoiceType(models.TextChoices):
        QUOTE = 'quote', 'Cotización'
        INVOICE = 'invoice', 'Factura'

    # Estados en los que el contenido económico ya no se puede modificar
    LOCKED_STATUSES = {Status.PAID, Status.CANCELLED}

    number = models.CharField(max_length=30)
    invoice_type = models.CharField(max_length=10, choices=InvoiceType.choices, default=InvoiceType.INVOICE)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    customer = models.ForeignKey('customers.Customer', on_delete=models.PROTECT, related_name='invoices')

    issue_date = models.DateField()
    due_date = models.DateField()

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'),
                                   validators=[MinValueValidator(Decimal('0'))])
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    notes = models.TextField(blank=True, default='')

    class Meta(AuthoredTenantModel.Meta):
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'number'], name='invoice_unique_number_per_tenant',
                                    violation_error_message='Ya existe un documento con este número.'),
            models.CheckConstraint(condition=models.Q(due_date__gte=models.F('issue_date')),
                                   name='invoice_due_after_issue'),
        ]
        indexes = [models.Index(fields=['tenant', 'status', 'issue_date'])]

    def __str__(self):
        return self.number


class InvoiceLine(TenantModel):
    """Línea con snapshot de precio, impuesto e importes al momento de facturar."""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='invoice_lines')
    description = models.CharField(max_length=300, blank=True, default='')
    quantity = models.DecimalField(max_digits=12, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    line_subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta(TenantModel.Meta):
        verbose_name = 'Línea de factura'
        verbose_name_plural = 'Líneas de factura'
        ordering = ['position', 'id']
