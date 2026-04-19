from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class Invoice(models.Model):
    """
    Factura o cotización emitida a un cliente.

    Una factura tiene una cabecera (este modelo) y líneas de detalle
    (InvoiceItem). Esta separación se llama patrón maestro-detalle
    y es estándar en todos los sistemas contables.
    """

    class Status(models.TextChoices):
        DRAFT    = 'draft',    'Borrador'
        SENT     = 'sent',     'Enviada'
        PAID     = 'paid',     'Pagada'
        OVERDUE  = 'overdue',  'Vencida'
        CANCELLED= 'cancelled','Cancelada'

    class InvoiceType(models.TextChoices):
        QUOTE   = 'quote',   'Cotización'
        INVOICE = 'invoice', 'Factura'

    # ── Identificación ──────────────────────────────
    number       = models.CharField(max_length=20, unique=True)  # Ej: FAC-2024-001
    invoice_type = models.CharField(max_length=10, choices=InvoiceType.choices, default=InvoiceType.INVOICE)
    status       = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    # ── Relaciones ───────────────────────────────────
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.PROTECT,  # PROTECT: no permite borrar un cliente con facturas
        related_name='invoices'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='invoices_created'
    )

    # ── Fechas ──────────────────────────────────────
    issue_date = models.DateField()
    due_date   = models.DateField()  # fecha límite de pago

    # ── Totales (se calculan automáticamente) ────────
    subtotal      = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    tax_amount    = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    discount      = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total         = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    notes = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering            = ['-created_at']

    def __str__(self):
        return f'{self.number} — {self.client}'

    def recalculate_totals(self):
        """
        Recalcula subtotal, impuestos y total a partir de las líneas.
        Se llama cada vez que se guarda o elimina un InvoiceItem.
        """
        items = self.items.all()
        subtotal   = sum(item.line_total for item in items)
        tax_amount = sum(item.tax_amount for item in items)
        self.subtotal   = subtotal
        self.tax_amount = tax_amount
        self.total      = subtotal + tax_amount - self.discount
        self.save(update_fields=['subtotal', 'tax_amount', 'total'])


class InvoiceItem(models.Model):
    """
    Línea de detalle de una factura.
    Cada línea representa un producto/servicio con su cantidad y precio.
    """
    invoice  = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product  = models.ForeignKey(
        'inventory.Product',
        on_delete=models.PROTECT,
        related_name='invoice_items'
    )

    # Guardamos el precio al momento de facturar
    # porque el precio del producto puede cambiar después
    quantity    = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    unit_price  = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate    = models.DecimalField(max_digits=5,  decimal_places=2, default=Decimal('19.00'))
    description = models.CharField(max_length=300, blank=True, default='')

    class Meta:
        verbose_name        = 'Línea de factura'
        verbose_name_plural = 'Líneas de factura'

    def __str__(self):
        return f'{self.invoice.number} — {self.product.name} x{self.quantity}'

    @property
    def line_total(self):
        """Subtotal de la línea sin impuestos."""
        return self.quantity * self.unit_price

    @property
    def tax_amount(self):
        """Impuesto de esta línea."""
        return self.line_total * (self.tax_rate / 100)

    @property
    def line_total_with_tax(self):
        return self.line_total + self.tax_amount

    def save(self, *args, **kwargs):
        # Al crear la línea, tomamos el precio actual del producto automáticamente
        if not self.pk and not self.unit_price:
            self.unit_price = self.product.price
            self.tax_rate   = self.product.tax_rate
        super().save(*args, **kwargs)
        # Recalculamos los totales de la factura padre
        self.invoice.recalculate_totals()

    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)
        # Al borrar una línea también recalculamos
        invoice.recalculate_totals()
