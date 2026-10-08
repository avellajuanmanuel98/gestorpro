from decimal import Decimal

from rest_framework import serializers

from gestorpro.core.api.serializers import TenantModelSerializer
from gestorpro.core.catalog.models import Product

from .models import Invoice, InvoiceLine


class InvoiceLineInputSerializer(serializers.Serializer):
    """Lo que el cliente PUEDE pedir. Importes e impuestos los calcula el servidor."""
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects)  # filtrado por tenant
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal('0.001'))
    unit_price = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0'), required=False)
    description = serializers.CharField(max_length=300, required=False, allow_blank=True)


class InvoiceLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = InvoiceLine
        fields = ['id', 'product', 'product_name', 'description', 'quantity', 'unit_price',
                  'tax_rate', 'line_subtotal', 'tax_amount', 'line_total']
        read_only_fields = fields


class InvoiceSerializer(TenantModelSerializer):
    """Lectura completa + validación de cabecera. La escritura la ejecuta services.save_invoice."""
    items = InvoiceLineInputSerializer(many=True, write_only=True, required=False)
    lines = InvoiceLineSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'tenant', 'number', 'invoice_type', 'status',
            'customer', 'customer_name', 'issue_date', 'due_date',
            'subtotal', 'tax_amount', 'discount', 'total',
            'notes', 'items', 'lines', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'subtotal', 'tax_amount', 'total', 'created_by', 'created_at', 'updated_at']

    def validate(self, attrs):
        issue = attrs.get('issue_date', getattr(self.instance, 'issue_date', None))
        due = attrs.get('due_date', getattr(self.instance, 'due_date', None))
        if issue and due and due < issue:
            raise serializers.ValidationError({'due_date': 'El vencimiento no puede ser anterior a la emisión.'})
        if self.instance is None and not attrs.get('items'):
            raise serializers.ValidationError({'items': 'El documento necesita al menos una línea.'})
        return attrs


class InvoiceListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'number', 'invoice_type', 'status', 'customer', 'customer_name',
                  'issue_date', 'due_date', 'total']
