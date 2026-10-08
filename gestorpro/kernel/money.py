"""
Dinero: aritmética decimal exacta y redondeo único para todo el sistema.

Reglas:
- Nunca float. Los importes entran como str/int/Decimal y salen como str en la API.
- Un único punto de redondeo: `money()` cuantiza a 2 decimales con ROUND_HALF_UP
  (el redondeo comercial habitual en Colombia).
- Los cálculos intermedios (cantidad × precio, base × tasa) se hacen con Decimal
  completo y se redondean al final de cada línea.
"""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal('0.01')
ZERO = Decimal('0.00')
HUNDRED = Decimal('100')


def to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        raise TypeError('No se aceptan float para dinero; usa str o Decimal.')
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f'Valor monetario inválido: {value!r}') from exc


def money(value) -> Decimal:
    """Cuantiza a centavos con redondeo comercial."""
    return to_decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def percentage_of(amount, rate) -> Decimal:
    """`rate` % de `amount`, redondeado. percentage_of('1000', '19') == Decimal('190.00')."""
    return money(to_decimal(amount) * to_decimal(rate) / HUNDRED)


def money_str(value) -> str:
    """Representación para JSON: string con 2 decimales (sin pérdida de precisión)."""
    return format(money(value if value is not None else ZERO), 'f')
