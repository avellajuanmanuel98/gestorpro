from django.apps import AppConfig


class ProductionConfig(AppConfig):
    name = 'gestorpro.capabilities.production'
    label = 'production'
    verbose_name = 'Recetas y producción'

    def ready(self):
        from gestorpro.core.inventory.services import set_recipe_resolver

        from .services import resolve_sale_consumption

        # Las bebidas preparadas del POS descuentan los ingredientes de su receta
        set_recipe_resolver(resolve_sale_consumption)
