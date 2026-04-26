from django.contrib import admin
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display  = ['name', 'slug', 'plan', 'city', 'is_active', 'created_at']
    list_filter   = ['plan', 'is_active']
    search_fields = ['name', 'slug', 'nit', 'email']
    readonly_fields = ['slug', 'created_at']
