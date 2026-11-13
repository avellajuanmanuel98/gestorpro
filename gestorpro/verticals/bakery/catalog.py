"""Configuración de catálogo del vertical Miga. Todas las funciones requieren el tenant activo."""
from gestorpro.core.catalog.models import Category, Item, UnitOfMeasure
from gestorpro.core.catalog.services import next_code

from .definition import MIGA, STARTER_INGREDIENTS


def ensure_default_categories() -> None:
    for name in MIGA.default_categories:
        Category.objects.get_or_create(name=name, kind=Category.Kind.PRODUCT)
    for name in MIGA.default_ingredient_categories:
        Category.objects.get_or_create(name=name, kind=Category.Kind.INGREDIENT)


def load_starter_ingredients() -> int:
    """
    Crea los ingredientes comunes que aún no existan (por nombre). Idempotente:
    no toca los que la panadería ya tenga, ni sus costos o existencias.
    Devuelve cuántos creó.
    """
    ensure_default_categories()
    categories = {c.name: c for c in Category.objects.filter(kind=Category.Kind.INGREDIENT)}
    units = {u.code: u for u in UnitOfMeasure.objects.all()}
    existing = {name.lower() for name in Item.objects.values_list('name', flat=True)}
    created = 0
    for name, category, unit in STARTER_INGREDIENTS:
        if name.lower() in existing:
            continue
        Item.objects.create(name=name, code=next_code(Item.Kind.RAW_MATERIAL), kind=Item.Kind.RAW_MATERIAL,
                            is_sellable=False, price=0, tax_rate=0, category=categories[category],
                            unit=units[unit])
        created += 1
    return created
