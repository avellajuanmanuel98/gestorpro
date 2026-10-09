from decimal import ROUND_HALF_UP, Decimal

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.validators import UniqueTogetherValidator

from gestorpro.core.api.serializers import TenantModelSerializer
from gestorpro.kernel.money import money_str

from . import services
from .models import Category, Item, UnitOfMeasure

# Campos que revelan el costo: solo los ve quien tiene `catalog.view_costs`
COST_FIELDS = ('avg_cost', 'stock_value', 'margin_pct')


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = ['code', 'name', 'symbol', 'dimension']


class CategorySerializer(TenantModelSerializer):
    items_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'tenant', 'name', 'description', 'kind', 'items_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_kind(self, value):
        if self.instance is not None and value != self.instance.kind and self.instance.items.exists():
            raise serializers.ValidationError('La categoría tiene ítems; no puede cambiar de tipo.')
        return value


def _can_see_costs(serializer) -> bool:
    request = serializer.context.get('request')
    membership = getattr(request, 'membership', None)
    return bool(membership and membership.has_perm('catalog.view_costs'))


class CostAwareMixin:
    """Oculta costo, valor de existencias y margen a quien no tiene `catalog.view_costs`."""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not _can_see_costs(self):
            for field in COST_FIELDS:
                data.pop(field, None)
        return data


class ItemSerializer(CostAwareMixin, TenantModelSerializer):
    unit = serializers.SlugRelatedField(slug_field='code', queryset=UnitOfMeasure.objects.all(), required=False)
    unit_symbol = serializers.CharField(source='unit.symbol', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    created_by = serializers.StringRelatedField(read_only=True)
    code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    stock_value = serializers.SerializerMethodField()
    margin_pct = serializers.SerializerMethodField()

    class Meta:
        model = Item
        fields = [
            'id', 'tenant', 'name', 'code', 'description', 'kind',
            'category', 'category_name', 'unit', 'unit_symbol', 'image',
            'is_sellable', 'price', 'tax_rate', 'avg_cost', 'margin_pct',
            'stock', 'minimum_stock', 'is_low_stock', 'stock_value',
            'is_active', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_stock_value(self, obj):
        return money_str(obj.stock_value)

    def get_margin_pct(self, obj):
        """Margen bruto sobre el precio antes de IVA. Null si falta precio o costo."""
        if not obj.is_sellable or obj.price <= 0 or obj.avg_cost <= 0:
            return None
        pct = (obj.price - obj.avg_cost) / obj.price * 100
        return str(pct.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))

    def get_validators(self):
        # La unicidad de `code` la valida services.normalize: así el código puede omitirse
        # (se genera) sin que DRF lo marque como obligatorio por pertenecer a (tenant, code).
        return [v for v in super().get_validators() if not isinstance(v, UniqueTogetherValidator)]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if 'avg_cost' in attrs and not _can_see_costs(self):
            raise PermissionDenied('No tienes permiso para registrar costos.')
        return services.normalize(attrs, self.instance)


class ItemListSerializer(CostAwareMixin, serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    unit = serializers.CharField(source='unit.code', read_only=True)
    unit_symbol = serializers.CharField(source='unit.symbol', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    stock_value = serializers.SerializerMethodField()
    margin_pct = serializers.SerializerMethodField()

    get_stock_value = ItemSerializer.get_stock_value
    get_margin_pct = ItemSerializer.get_margin_pct

    class Meta:
        model = Item
        fields = ['id', 'name', 'code', 'kind', 'category', 'category_name', 'unit', 'unit_symbol',
                  'is_sellable', 'price', 'tax_rate', 'avg_cost', 'margin_pct',
                  'stock', 'minimum_stock', 'is_low_stock', 'stock_value', 'is_active']
