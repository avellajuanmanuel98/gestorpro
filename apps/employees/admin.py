from django.contrib import admin
from .models import Employee


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display  = ['full_name', 'position', 'department', 'email', 'status', 'company']
    list_filter   = ['status', 'department', 'company']
    search_fields = ['first_name', 'last_name', 'email', 'document_number']
    ordering      = ['first_name']
