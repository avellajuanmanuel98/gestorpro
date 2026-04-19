from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class Category(models.Model):
    """
    Categoría de productos. Ej: Electrónica, Ropa, Servicios.
    Separamos categorías de productos para poder filtrar y organizar.
    """
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering            = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Producto o servicio que la empresa vende.
    Puede ser un producto físico (con stock) o un servicio (sin stock).
    """

    class ProductType(models.TextChoices):
        PRODUCT = 'product', 'Producto'
        SERVICE = 'service', 'Servicio'

    # ── Información básica ──────────────────────────
    name        = models.CharField(max_length=200)
    code        = models.CharField(max_length=50, unique=True)  # SKU o código interno
    description = models.TextField(blank=True, default='')
    product_type = models.CharField(max_length=10, choices=ProductType.choices, default=ProductType.PRODUCT)
    category    = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    image = models.ImageField(upload_to='products/', null=True, blank=True)

    # ── Precios ─────────────────────────────────────
    # Usamos Decimal para dinero, NUNCA float
    # float tiene errores de precisión: 0.1 + 0.2 = 0.30000000000000004
    price     = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_rate  = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('19.00'),  # IVA Colombia 19%
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    # ── Stock (solo aplica a productos físicos) ──────
    stock         = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    minimum_stock = models.IntegerField(default=5)  # alerta cuando baje de este número

    # ── Estado ──────────────────────────────────────
    is_active  = models.BooleanField(default=True)

    # ── Auditoría ────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Producto'
        verbose_name_plural = 'Productos'
        ordering            = ['name']

    def __str__(self):
        return f'{self.code} — {self.name}'

    @property
    def is_low_stock(self):
        """True si el stock está por debajo del mínimo configurado."""
        return self.product_type == 'product' and self.stock <= self.minimum_stock

    @property
    def price_with_tax(self):
        """Precio final con IVA incluido."""
        return self.price * (1 + self.tax_rate / 100)
