from rest_framework import serializers

from gestorpro.core.customers.models import Customer
from gestorpro.kernel.money import money, money_str, percentage_of

from .models import Payment, PaymentMethod, Sale, SaleLine


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'code', 'name', 'kind']


class POSItemSerializer(serializers.Serializer):
    """Ítem del catálogo del POS. `price_with_tax` es lo que paga el cliente por unidad."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()
    category = serializers.IntegerField(source='category_id', allow_null=True)
    unit = serializers.CharField(source='unit.code')
    unit_symbol = serializers.CharField(source='unit.symbol')
    price = serializers.DecimalField(max_digits=14, decimal_places=2)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    price_with_tax = serializers.SerializerMethodField()
    stock = serializers.DecimalField(max_digits=14, decimal_places=4)
    tracks_stock = serializers.BooleanField()

    def get_price_with_tax(self, obj):
        return money_str(money(obj.price) + percentage_of(obj.price, obj.tax_rate))


# ── Entrada: lo que el POS PUEDE pedir (todo lo económico lo calcula el servidor) ──

class SaleLineInputSerializer(serializers.Serializer):
    item = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=4)


class PaymentInputSerializer(serializers.Serializer):
    method = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    reference = serializers.CharField(max_length=60, required=False, allow_blank=True)


class SaleCreateSerializer(serializers.Serializer):
    client_uuid = serializers.UUIDField()
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects, required=False, allow_null=True)
    discount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    lines = SaleLineInputSerializer(many=True)
    payments = PaymentInputSerializer(many=True)


# ── Salida ──────────────────────────────────────────────────────────────────

class SaleLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleLine
        fields = ['id', 'item', 'item_name', 'unit_symbol', 'quantity', 'unit_price', 'tax_rate',
                  'line_subtotal', 'tax_amount', 'line_total']


class PaymentSerializer(serializers.ModelSerializer):
    method_name = serializers.CharField(source='method.name')
    method_kind = serializers.CharField(source='method.kind')

    class Meta:
        model = Payment
        fields = ['id', 'method', 'method_name', 'method_kind', 'amount', 'tendered', 'reference']


def _name(user):
    return (user.full_name or user.email) if user else None


class SaleListSerializer(serializers.ModelSerializer):
    cashier_name = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source='customer.full_name')
    payment_summary = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ['id', 'number', 'status', 'created_at', 'cashier_name', 'customer_name', 'total',
                  'payment_summary']

    def get_cashier_name(self, obj):
        return _name(obj.cashier)

    def get_payment_summary(self, obj):
        return ', '.join(sorted({p.method.name for p in obj.payments.all()}))


class SaleSerializer(SaleListSerializer):
    lines = SaleLineSerializer(many=True)
    payments = PaymentSerializer(many=True)
    location_name = serializers.CharField(source='location.name')
    register_name = serializers.CharField(source='cash_session.register.name')
    voided_by_name = serializers.SerializerMethodField()
    can_void = serializers.SerializerMethodField()

    class Meta(SaleListSerializer.Meta):
        fields = SaleListSerializer.Meta.fields + [
            'location_name', 'register_name', 'subtotal', 'tax_total', 'discount', 'change_given',
            'lines', 'payments', 'voided_at', 'voided_by_name', 'void_reason', 'fiscal_status', 'can_void',
        ]

    def get_voided_by_name(self, obj):
        return _name(obj.voided_by)

    def get_can_void(self, obj):
        request = self.context.get('request')
        membership = getattr(request, 'membership', None)
        return bool(membership and membership.has_perm('sales.void') and obj.status == Sale.Status.COMPLETED
                    and obj.cash_session.is_open)


class VoidSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=200)
