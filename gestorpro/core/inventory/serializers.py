from rest_framework import serializers

from .models import StockMovement


def _name(user):
    return (user.full_name or user.email) if user else None


class StockMovementSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name')
    unit_symbol = serializers.CharField(source='item.unit.symbol')
    location_name = serializers.CharField(source='location.name')
    type_label = serializers.CharField(source='get_type_display')
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = ['id', 'item', 'item_name', 'unit_symbol', 'location_name', 'type', 'type_label', 'quantity',
                  'unit_cost', 'total_cost', 'balance_after', 'avg_cost_after', 'source_type', 'source_id',
                  'source_label', 'reason', 'created_by_name', 'created_at']

    def get_created_by_name(self, obj):
        return _name(obj.created_by)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if not (request and request.membership.has_perm('catalog.view_costs')):
            for field in ('unit_cost', 'total_cost', 'avg_cost_after'):
                data.pop(field, None)
        return data


class CountLineSerializer(serializers.Serializer):
    item = serializers.IntegerField()
    counted = serializers.DecimalField(max_digits=16, decimal_places=4)


class CountSerializer(serializers.Serializer):
    location = serializers.IntegerField(required=False)
    counts = CountLineSerializer(many=True)
    note = serializers.CharField(max_length=200, required=False, allow_blank=True)
