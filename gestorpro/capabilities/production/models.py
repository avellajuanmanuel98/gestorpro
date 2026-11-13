"""
Recetas y producción.

    Recipe ─< RecipeLine >─ Item (ingrediente)         ¿Qué lleva y cuánto rinde?
    ProductionBatch ─< ProductionConsumption >─ Item     ¿Qué se produjo y qué se gastó de verdad?

- Una receta pertenece a un producto elaborado y tiene VERSIONES. Si una
  versión ya se usó en producción, cambiarla crea una versión nueva: los
  lotes anteriores conservan la receta y el costo con que se hicieron.
- Un lote consume los ingredientes REALES (pueden diferir de la receta) al
  costo promedio vigente y genera el producto con costo = Σ consumos. Ese
  costo entra al promedio ponderado del producto.
"""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from gestorpro.core.tenancy.db import TenantModel


class Recipe(TenantModel):
    product = models.ForeignKey('catalog.Item', verbose_name='producto', on_delete=models.PROTECT,
                                related_name='recipes')
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    yield_quantity = models.DecimalField(verbose_name='rendimiento', max_digits=14, decimal_places=4,
                                         help_text='Cuánto producto sale, en la unidad del producto.')
    notes = models.TextField(verbose_name='preparación / notas', blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')

    class Meta(TenantModel.Meta):
        verbose_name = 'Receta'
        ordering = ['product__name', '-version']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'product', 'version'], name='recipe_unique_version'),
            models.UniqueConstraint(fields=['product'], condition=Q(is_active=True), name='recipe_one_active'),
            models.CheckConstraint(condition=Q(yield_quantity__gt=0), name='recipe_yield_positive'),
        ]

    def __str__(self):
        return f'{self.product.name} v{self.version}'


class RecipeLine(TenantModel):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='lines')
    ingredient = models.ForeignKey('catalog.Item', on_delete=models.PROTECT, related_name='used_in_recipes')
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    unit = models.ForeignKey('catalog.UnitOfMeasure', on_delete=models.PROTECT, related_name='+')
    waste_pct = models.DecimalField(verbose_name='% de desperdicio', max_digits=5, decimal_places=2, default=0,
                                    validators=[MinValueValidator(0), MaxValueValidator(100)])
    sort = models.PositiveSmallIntegerField(default=0)

    class Meta(TenantModel.Meta):
        verbose_name = 'Ingrediente de receta'
        ordering = ['sort', 'id']
        constraints = [models.CheckConstraint(condition=Q(quantity__gt=0), name='recipe_line_quantity_positive')]


class ProductionBatch(TenantModel):
    number = models.CharField(max_length=30)
    location = models.ForeignKey('tenancy.Location', on_delete=models.PROTECT, related_name='+')
    recipe = models.ForeignKey(Recipe, on_delete=models.PROTECT, related_name='batches')
    product = models.ForeignKey('catalog.Item', on_delete=models.PROTECT, related_name='production_batches')
    produced_quantity = models.DecimalField(verbose_name='cantidad producida', max_digits=14, decimal_places=4)
    total_cost = models.DecimalField(max_digits=16, decimal_places=4)
    unit_cost = models.DecimalField(max_digits=16, decimal_places=4)
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')

    class Meta(TenantModel.Meta):
        verbose_name = 'Lote de producción'
        verbose_name_plural = 'Lotes de producción'
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'location', 'number'], name='production_unique_number'),
            models.CheckConstraint(condition=Q(produced_quantity__gt=0), name='production_quantity_positive'),
        ]


class ProductionConsumption(TenantModel):
    batch = models.ForeignKey(ProductionBatch, on_delete=models.CASCADE, related_name='consumptions')
    ingredient = models.ForeignKey('catalog.Item', on_delete=models.PROTECT, related_name='+')
    planned_quantity = models.DecimalField(max_digits=16, decimal_places=4)
    actual_quantity = models.DecimalField(max_digits=16, decimal_places=4)
    unit_cost = models.DecimalField(max_digits=16, decimal_places=4)
    total_cost = models.DecimalField(max_digits=18, decimal_places=4)

    class Meta(TenantModel.Meta):
        verbose_name = 'Consumo de producción'
        ordering = ['id']
