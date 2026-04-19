from rest_framework import serializers
from .models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    product_name      = serializers.CharField(source='product.name', read_only=True)
    line_total        = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    tax_amount        = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    line_total_with_tax = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model  = InvoiceItem
        fields = [
            'id', 'product', 'product_name', 'description',
            'quantity', 'unit_price', 'tax_rate',
            'line_total', 'tax_amount', 'line_total_with_tax',
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    items      = InvoiceItemSerializer(many=True)
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    created_by  = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = Invoice
        fields = [
            'id', 'number', 'invoice_type', 'status',
            'client', 'client_name',
            'issue_date', 'due_date',
            'subtotal', 'tax_amount', 'discount', 'total',
            'notes', 'items',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'subtotal', 'tax_amount', 'total', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Separamos los items de los datos de la factura
        items_data = validated_data.pop('items')

        # Creamos la factura primero
        invoice = Invoice.objects.create(**validated_data)

        # Luego creamos cada línea de detalle
        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)

        # Los totales se calcularon automáticamente en el save() de cada item
        invoice.refresh_from_db()
        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        # Actualizamos campos de la cabecera
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Si enviaron items, reemplazamos los existentes
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                InvoiceItem.objects.create(invoice=instance, **item_data)
            instance.refresh_from_db()

        return instance


class InvoiceListSerializer(serializers.ModelSerializer):
    """Versión reducida para el listado."""
    client_name = serializers.CharField(source='client.full_name', read_only=True)

    class Meta:
        model  = Invoice
        fields = [
            'id', 'number', 'invoice_type', 'status',
            'client_name', 'issue_date', 'due_date', 'total',
        ]
