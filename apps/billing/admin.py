from django.contrib import admin
from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model  = InvoiceItem
    extra  = 1
    fields = ['product', 'description', 'quantity', 'unit_price', 'tax_rate']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display    = ['number', 'invoice_type', 'client', 'status', 'total', 'issue_date', 'due_date']
    list_filter     = ['status', 'invoice_type', 'issue_date']
    search_fields   = ['number', 'client__first_name', 'client__last_name']
    readonly_fields = ['subtotal', 'tax_amount', 'total', 'created_by', 'created_at', 'updated_at']
    inlines         = [InvoiceItemInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
