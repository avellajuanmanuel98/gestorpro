"""
Cantidades y conversión de unidades de medida.

Reglas:
- Nunca float. Las cantidades son Decimal con hasta 4 decimales (gramos de
  harina, fracciones de unidad).
- Cada unidad pertenece a una DIMENSIÓN (masa, volumen, conteo) y declara su
  factor respecto a la unidad base de esa dimensión (g, ml, und).
- Solo se convierte dentro de la misma dimensión: kilos a gramos sí; kilos a
  litros no. Pasar de masa a volumen exige una densidad, que dependería del
  ingrediente; si algún día hace falta, será una conversión explícita por
  ítem, nunca una suposición.

La conversión vive aquí, en un único lugar con tests, porque un error de
unidades rompe el costo de todas las recetas (riesgo R3 del documento 01).
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .money import to_decimal

QTY = Decimal('0.0001')


class Dimension:
    MASS = 'mass'
    VOLUME = 'volume'
    COUNT = 'count'


class IncompatibleUnits(ValueError):
    """Conversión entre dimensiones distintas (p. ej. kg → l)."""


@dataclass(frozen=True)
class Unit:
    code: str
    dimension: str
    factor: Decimal  # cuántas unidades base de su dimensión equivalen a 1 de esta unidad


def quantity(value) -> Decimal:
    """Cuantiza una cantidad a 4 decimales (redondeo comercial). Rechaza float."""
    return to_decimal(value).quantize(QTY, rounding=ROUND_HALF_UP)


def convert(value, source: Unit, target: Unit) -> Decimal:
    """Convierte `value` de `source` a `target`. convert(1.5, kg, g) == 1500."""
    if source.dimension != target.dimension:
        raise IncompatibleUnits(f'No se puede convertir {source.code} a {target.code}.')
    if source.code == target.code:
        return quantity(value)
    return quantity(to_decimal(value) * source.factor / target.factor)


def cost_per(unit_cost, source: Unit, target: Unit) -> Decimal:
    """
    Reexpresa un costo unitario en otra unidad, sin redondear a centavos:
    $3.200 por kg == $3,2 por g. Es la operación inversa de `convert`.
    """
    if source.dimension != target.dimension:
        raise IncompatibleUnits(f'No se puede convertir {source.code} a {target.code}.')
    return to_decimal(unit_cost) * target.factor / source.factor
