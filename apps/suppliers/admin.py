from django.contrib import admin
from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display  = ['company_name', 'contact_name', 'category', 'email', 'status', 'company']
    list_filter   = ['status', 'category', 'company']
    search_fields = ['company_name', 'contact_name', 'email', 'document_number']
    ordering      = ['company_name']
