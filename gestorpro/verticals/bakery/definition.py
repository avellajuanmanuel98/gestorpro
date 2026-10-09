"""
Definición del vertical Miga (panaderías).

Un vertical es configuración + composición de módulos, no un fork del Core:
no define entidades propias para cosas comunes (no existe PanaderiaProduct;
existe el Item del Core). Se engancha al alta de empresas mediante la señal
`tenant_provisioned`.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class VerticalDefinition:
    key: str
    brand: dict
    default_categories: list[str] = field(default_factory=list)
    default_ingredient_categories: list[str] = field(default_factory=list)
    recommended_plan: str = 'business'


MIGA = VerticalDefinition(
    key='bakery',
    brand={'product': 'Miga', 'endorsement': 'by GestorPro', 'tagline': 'Gestión inteligente para panaderías'},
    default_categories=['Panes', 'Panes rellenos', 'Hojaldres', 'Tortas y postres', 'Galletería',
                        'Bebidas calientes', 'Bebidas frías', 'Lácteos y otros'],
    default_ingredient_categories=['Harinas y almidones', 'Lácteos y huevos', 'Grasas', 'Endulzantes',
                                   'Levaduras y aditivos', 'Rellenos y frutas', 'Bebidas e insumos de cafetería',
                                   'Empaques'],
)

# Catálogo base de ingredientes de una panadería colombiana: nombre, categoría,
# unidad. Sin costos ni existencias: cada panadería registra los suyos.
STARTER_INGREDIENTS = [
    ('Harina de trigo', 'Harinas y almidones', 'kg'),
    ('Harina de trigo integral', 'Harinas y almidones', 'kg'),
    ('Almidón de yuca', 'Harinas y almidones', 'kg'),
    ('Harina de maíz precocida', 'Harinas y almidones', 'kg'),
    ('Fécula de maíz', 'Harinas y almidones', 'kg'),
    ('Leche entera', 'Lácteos y huevos', 'l'),
    ('Huevos', 'Lácteos y huevos', 'und'),
    ('Queso costeño', 'Lácteos y huevos', 'kg'),
    ('Cuajada', 'Lácteos y huevos', 'kg'),
    ('Queso doble crema', 'Lácteos y huevos', 'kg'),
    ('Crema de leche', 'Lácteos y huevos', 'l'),
    ('Mantequilla', 'Grasas', 'kg'),
    ('Margarina de hojaldre', 'Grasas', 'kg'),
    ('Aceite vegetal', 'Grasas', 'l'),
    ('Azúcar blanca', 'Endulzantes', 'kg'),
    ('Azúcar morena', 'Endulzantes', 'kg'),
    ('Panela', 'Endulzantes', 'kg'),
    ('Levadura fresca', 'Levaduras y aditivos', 'kg'),
    ('Levadura seca', 'Levaduras y aditivos', 'kg'),
    ('Sal', 'Levaduras y aditivos', 'kg'),
    ('Polvo de hornear', 'Levaduras y aditivos', 'kg'),
    ('Esencia de vainilla', 'Levaduras y aditivos', 'ml'),
    ('Arequipe', 'Rellenos y frutas', 'kg'),
    ('Bocadillo de guayaba', 'Rellenos y frutas', 'kg'),
    ('Uvas pasas', 'Rellenos y frutas', 'kg'),
    ('Chocolate de mesa', 'Rellenos y frutas', 'kg'),
    ('Café molido', 'Bebidas e insumos de cafetería', 'kg'),
    ('Bolsa de papel pequeña', 'Empaques', 'und'),
    ('Bolsa de papel grande', 'Empaques', 'und'),
    ('Caja para torta', 'Empaques', 'und'),
    ('Vaso desechable 7 oz', 'Empaques', 'und'),
]
