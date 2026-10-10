from rest_framework import serializers

from gestorpro.core.catalog.models import Item

from . import services
from .models import ProductionBatch, ProductionConsumption, Recipe


def can_see_costs(context) -> bool:
    request = context.get('request')
    return bool(request and request.membership.has_perm('catalog.view_costs'))


class RecipeLineInputSerializer(serializers.Serializer):
    ingredient = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=4)
    unit = serializers.CharField(max_length=12, required=False)
    waste_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)


class RecipeInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Item.objects)
    yield_quantity = serializers.DecimalField(max_digits=14, decimal_places=4)
    notes = serializers.CharField(required=False, allow_blank=True)
    lines = RecipeLineInputSerializer(many=True)


class RecipeSerializer(serializers.ModelSerializer):
    """Receta con su costo estimado (solo con permiso de costos)."""
    product_name = serializers.CharField(source='product.name')
    product_unit = serializers.CharField(source='product.unit.symbol')
    product_price = serializers.DecimalField(source='product.price', max_digits=14, decimal_places=2)
    consume_on_sale = serializers.BooleanField(source='product.consume_on_sale')
    lines = serializers.SerializerMethodField()
    cost = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ['id', 'product', 'product_name', 'product_unit', 'product_price', 'consume_on_sale', 'version',
                  'is_active', 'yield_quantity', 'notes', 'lines', 'cost', 'created_at', 'updated_at']

    def _costing(self, obj):
        if not hasattr(obj, '_costing'):
            obj._costing = services.recipe_cost(obj)
        return obj._costing

    def get_lines(self, obj):
        show = can_see_costs(self.context)
        rows = []
        for entry in self._costing(obj)['lines']:
            line = entry['line']
            row = {'id': line.id, 'ingredient': line.ingredient_id, 'ingredient_name': line.ingredient.name,
                   'quantity': str(line.quantity), 'unit': line.unit.code, 'unit_symbol': line.unit.symbol,
                   'waste_pct': str(line.waste_pct), 'ingredient_unit': line.ingredient.unit.symbol,
                   'ingredient_unit_code': line.ingredient.unit.code,
                   'base_quantity': str(entry['base_quantity'])}
            if show:
                row.update(cost=str(entry['cost']), ingredient_avg_cost=str(line.ingredient.avg_cost),
                           missing_cost=entry['missing_cost'])
            rows.append(row)
        return rows

    def get_cost(self, obj):
        if not can_see_costs(self.context):
            return None
        c = self._costing(obj)
        return {'total': str(c['total']), 'unit_cost': str(c['unit_cost']),
                'margin_pct': str(c['margin_pct']) if c['margin_pct'] is not None else None, 'complete': c['complete']}


class ProduceSerializer(serializers.Serializer):
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects)
    quantity = serializers.DecimalField(max_digits=14, decimal_places=4)
    actual = serializers.DictField(child=serializers.DecimalField(max_digits=16, decimal_places=4), required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class ConsumptionSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name')
    unit_symbol = serializers.CharField(source='ingredient.unit.symbol')

    class Meta:
        model = ProductionConsumption
        fields = ['ingredient', 'ingredient_name', 'unit_symbol', 'planned_quantity', 'actual_quantity',
                  'unit_cost', 'total_cost']


class BatchSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name')
    unit_symbol = serializers.CharField(source='product.unit.symbol')
    recipe_version = serializers.IntegerField(source='recipe.version')
    created_by_name = serializers.SerializerMethodField()
    consumptions = ConsumptionSerializer(many=True)

    class Meta:
        model = ProductionBatch
        fields = ['id', 'number', 'product', 'product_name', 'unit_symbol', 'recipe', 'recipe_version',
                  'produced_quantity', 'total_cost', 'unit_cost', 'notes', 'created_by_name', 'created_at',
                  'consumptions']

    def get_created_by_name(self, obj):
        return obj.created_by.full_name or obj.created_by.email

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not can_see_costs(self.context):
            data.pop('total_cost'), data.pop('unit_cost')
            for row in data['consumptions']:
                row.pop('unit_cost'), row.pop('total_cost')
        return data
