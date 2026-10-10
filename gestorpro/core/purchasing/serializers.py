from rest_framework import serializers

from gestorpro.core.suppliers.models import Supplier

from .models import PurchaseLine, PurchaseReceipt


class PurchaseLineInputSerializer(serializers.Serializer):
    item = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=4)
    unit = serializers.CharField(max_length=12, required=False)
    unit_cost = serializers.DecimalField(max_digits=14, decimal_places=4)


class PurchaseCreateSerializer(serializers.Serializer):
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects, required=False, allow_null=True)
    supplier_invoice = serializers.CharField(max_length=60, required=False, allow_blank=True)
    received_on = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True)
    lines = PurchaseLineInputSerializer(many=True)


class PurchaseLineSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name')
    unit_symbol = serializers.CharField(source='unit.symbol')
    item_unit_symbol = serializers.CharField(source='item.unit.symbol')

    class Meta:
        model = PurchaseLine
        fields = ['id', 'item', 'item_name', 'quantity', 'unit_symbol', 'unit_cost', 'total',
                  'base_quantity', 'item_unit_symbol', 'base_unit_cost']


class PurchaseSerializer(serializers.ModelSerializer):
    supplier_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    lines_count = serializers.IntegerField(source='lines.count', read_only=True)

    class Meta:
        model = PurchaseReceipt
        fields = ['id', 'number', 'supplier', 'supplier_name', 'supplier_invoice', 'received_on', 'total', 'notes',
                  'created_by_name', 'created_at', 'lines_count']

    def get_supplier_name(self, obj):
        return str(obj.supplier) if obj.supplier else None

    def get_created_by_name(self, obj):
        return obj.created_by.full_name or obj.created_by.email


class PurchaseDetailSerializer(PurchaseSerializer):
    lines = PurchaseLineSerializer(many=True)

    class Meta(PurchaseSerializer.Meta):
        fields = PurchaseSerializer.Meta.fields + ['lines']
