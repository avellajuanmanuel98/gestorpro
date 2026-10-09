"""
Catálogo del Core: unidades de medida, categorías e ítems.

Un único modelo `Item` para todo lo que la empresa vende, compra o almacena
(decisión D-6). El `kind` define qué es conceptualmente:

    finished_good  Producto elaborado  (pan, torta)      se produce y se vende
    resale         Reventa             (gaseosa)         se compra y se vende
    raw_material   Insumo/ingrediente  (harina, bolsas)  se compra y se consume
    service        Servicio            (domicilio)       se vende, no tiene existencias

La UI los presenta en pantallas distintas (Productos / Ingredientes). Un insumo
puede marcarse también como vendible (el queso que se vende por libra) sin
duplicarlo: compras, existencias, costo y mermas aplican igual a ambos.

Existencias y costo (TRANSITORIO hasta la Fase 8):
- `stock` y `minimum_stock` se expresan en la unidad del ítem (`unit`).
- `avg_cost` es el costo por unidad del ítem. Hoy lo registra la empresa como
  costo de referencia. En la Fase 8 pasará a calcularse por promedio ponderado
  desde el libro de movimientos, y `stock` dejará de editarse a mano (el valor
  actual se convertirá en un movimiento de "saldo inicial").
"""
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from gestorpro.core.tenancy.db import AuthoredTenantModel, TenantModel
from gestorpro.kernel import units


class UnitOfMeasure(models.Model):
    """Unidad de medida GLOBAL (igual para todas las empresas); se siembra por migración."""

    class Dimension(models.TextChoices):
        MASS = units.Dimension.MASS, 'Masa'
        VOLUME = units.Dimension.VOLUME, 'Volumen'
        COUNT = units.Dimension.COUNT, 'Conteo'

    code = models.CharField(verbose_name='código', max_length=12, unique=True)
    name = models.CharField(verbose_name='nombre', max_length=40)
    symbol = models.CharField(verbose_name='símbolo', max_length=12)
    dimension = models.CharField(verbose_name='dimensión', max_length=10, choices=Dimension.choices)
    factor = models.DecimalField(
        verbose_name='factor a la unidad base', max_digits=18, decimal_places=6,
        help_text='Unidades base (g, ml, und) que equivalen a 1 de esta unidad.',
    )
    sort = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Unidad de medida'
        verbose_name_plural = 'Unidades de medida'
        ordering = ['dimension', 'sort', 'code']

    def __str__(self):
        return self.symbol

    def as_unit(self) -> units.Unit:
        return units.Unit(code=self.code, dimension=self.dimension, factor=self.factor)


class Category(TenantModel):

    class Kind(models.TextChoices):
        PRODUCT = 'product', 'Productos'
        INGREDIENT = 'ingredient', 'Ingredientes'

    name = models.CharField(verbose_name='nombre', max_length=100)
    description = models.TextField(verbose_name='descripción', blank=True, default='')
    kind = models.CharField(verbose_name='tipo', max_length=12, choices=Kind.choices, default=Kind.PRODUCT)

    class Meta(TenantModel.Meta):
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'kind', 'name'], name='category_unique_name_per_kind',
                                    violation_error_message='Ya existe una categoría con este nombre.'),
        ]

    def __str__(self):
        return self.name


class Item(AuthoredTenantModel):

    class Kind(models.TextChoices):
        FINISHED_GOOD = 'finished_good', 'Producto elaborado'
        RESALE = 'resale', 'Reventa'
        RAW_MATERIAL = 'raw_material', 'Ingrediente o insumo'
        SERVICE = 'service', 'Servicio'

    # Tipos que se gestionan en la pantalla de Productos (siempre vendibles)
    PRODUCT_KINDS = (Kind.FINISHED_GOOD, Kind.RESALE, Kind.SERVICE)

    name = models.CharField(verbose_name='nombre', max_length=200)
    code = models.CharField(verbose_name='código', max_length=50)  # SKU interno, único por empresa
    description = models.TextField(verbose_name='descripción', blank=True, default='')
    kind = models.CharField(verbose_name='tipo', max_length=16, choices=Kind.choices, default=Kind.FINISHED_GOOD)
    category = models.ForeignKey(
        Category, verbose_name='categoría', on_delete=models.SET_NULL, null=True, blank=True, related_name='items',
    )
    unit = models.ForeignKey(UnitOfMeasure, verbose_name='unidad', on_delete=models.PROTECT, related_name='+')
    image = models.ImageField(verbose_name='imagen', upload_to='products/', null=True, blank=True)

    is_sellable = models.BooleanField(verbose_name='se vende', default=True)
    price = models.DecimalField(
        verbose_name='precio de venta', max_digits=14, decimal_places=2, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
    )
    tax_rate = models.DecimalField(
        verbose_name='IVA %',
        max_digits=5, decimal_places=2, default=Decimal('19.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
    )
    avg_cost = models.DecimalField(
        verbose_name='costo por unidad', max_digits=14, decimal_places=4, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
    )

    stock = models.DecimalField(verbose_name='existencia', max_digits=14, decimal_places=4, default=Decimal('0'),
                                validators=[MinValueValidator(Decimal('0'))])
    minimum_stock = models.DecimalField(verbose_name='existencia mínima', max_digits=14, decimal_places=4,
                                        default=Decimal('0'), validators=[MinValueValidator(Decimal('0'))])
    is_active = models.BooleanField(verbose_name='activo', default=True)

    # Auditoría: cambios de precio, impuesto o costo generan un evento propio
    audit_field_events = {
        'price': 'catalog.item.price_changed',
        'tax_rate': 'catalog.item.tax_changed',
        'avg_cost': 'catalog.item.cost_changed',
    }

    class Meta(AuthoredTenantModel.Meta):
        verbose_name = 'Ítem'
        verbose_name_plural = 'Ítems'
        ordering = ['name', 'id']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'code'], name='item_unique_code_per_tenant',
                                    violation_error_message='Ya existe un ítem con este código.'),
            # Los productos siempre se venden; un servicio no tiene existencias
            models.CheckConstraint(
                condition=models.Q(kind='raw_material') | models.Q(is_sellable=True),
                name='item_products_are_sellable',
            ),
            models.CheckConstraint(
                condition=~models.Q(kind='service') | (models.Q(stock=0) & models.Q(minimum_stock=0)),
                name='item_service_without_stock',
            ),
        ]
        indexes = [models.Index(fields=['tenant', 'kind', 'is_active'])]

    def __str__(self):
        return f'{self.code} — {self.name}'

    @property
    def tracks_stock(self) -> bool:
        return self.kind != self.Kind.SERVICE

    @property
    def is_low_stock(self) -> bool:
        return self.tracks_stock and self.minimum_stock > 0 and self.stock <= self.minimum_stock

    @property
    def stock_value(self) -> Decimal:
        """Valor de la existencia a costo (no a precio de venta)."""
        return self.stock * self.avg_cost if self.tracks_stock else Decimal('0')
