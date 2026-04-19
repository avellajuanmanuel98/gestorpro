from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display   = ['full_name', 'company_name', 'email', 'phone', 'city', 'status']
    list_filter    = ['status', 'document_type', 'city']
    search_fields  = ['first_name', 'last_name', 'email', 'document_number', 'company_name']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    ordering       = ['first_name']
