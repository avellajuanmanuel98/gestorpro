from rest_framework import serializers

from .models import WasteReason, WasteRecord


class WasteReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteReason
        fields = ['id', 'code', 'name']


class WasteInputSerializer(serializers.Serializer):
    item = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=4)
    reason = serializers.PrimaryKeyRelatedField(queryset=WasteReason.objects)
    notes = serializers.CharField(max_length=200, required=False, allow_blank=True)


class WasteRecordSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name')
    unit_symbol = serializers.CharField(source='item.unit.symbol')
    reason_name = serializers.CharField(source='reason.name')
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = WasteRecord
        fields = ['id', 'item', 'item_name', 'unit_symbol', 'quantity', 'reason', 'reason_name', 'unit_cost',
                  'total_cost', 'notes', 'created_by_name', 'created_at']

    def get_created_by_name(self, obj):
        return obj.created_by.full_name or obj.created_by.email

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if not (request and request.membership.has_perm('catalog.view_costs')):
            data.pop('unit_cost'), data.pop('total_cost')
        return data
