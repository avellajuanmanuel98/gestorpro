"""
Definición del vertical Miga (panaderías).

Un vertical es configuración + composición de módulos, no un fork del Core:
no define entidades propias para cosas comunes (no existe PanaderiaProduct).
Se engancha al alta de empresas mediante la señal `tenant_provisioned`.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class VerticalDefinition:
    key: str
    brand: dict
    default_categories: list[str] = field(default_factory=list)
    recommended_plan: str = 'business'


MIGA = VerticalDefinition(
    key='bakery',
    brand={'product': 'Miga', 'endorsement': 'by GestorPro', 'tagline': 'Gestión inteligente para panaderías'},
    default_categories=['Panes', 'Panes rellenos', 'Hojaldres', 'Tortas y postres',
                        'Bebidas calientes', 'Bebidas frías'],
)

# Compatibilidad con el seed existente
BRAND = MIGA.brand
DEFAULT_CATEGORIES = MIGA.default_categories
