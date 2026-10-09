from django.contrib import admin

from gestorpro.core.access.models import Membership, Role
from gestorpro.core.audit.models import SecurityEvent
from gestorpro.core.identity.models import User
from gestorpro.core.tenancy.models import Location, Tenant
from gestorpro.platform.subscriptions.models import Plan, PlanFeature, PlanLimit, Subscription

from .site import UnscopedReadOnlyAdmin, platform_admin_site


@admin.register(Tenant, site=platform_admin_site)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'vertical', 'status', 'city', 'created_at']
    list_filter = ['vertical', 'status']
    search_fields = ['name', 'slug', 'tax_id', 'email']
    readonly_fields = ['slug', 'created_at', 'updated_at']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(User, site=platform_admin_site)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'is_active', 'is_platform_admin', 'last_login']
    list_filter = ['is_active', 'is_platform_admin']
    search_fields = ['email', 'first_name', 'last_name']
    fields = ['email', 'first_name', 'last_name', 'is_active', 'last_login', 'date_joined']
    readonly_fields = ['email', 'last_login', 'date_joined']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Membership, site=platform_admin_site)
class MembershipAdmin(UnscopedReadOnlyAdmin):
    list_display = ['user', 'tenant', 'role', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['user__email', 'tenant__name']


@admin.register(Role, site=platform_admin_site)
class RoleAdmin(UnscopedReadOnlyAdmin):
    list_display = ['name', 'code', 'tenant', 'is_system']
    search_fields = ['tenant__name', 'code']


@admin.register(Location, site=platform_admin_site)
class LocationAdmin(UnscopedReadOnlyAdmin):
    list_display = ['name', 'tenant', 'is_default', 'is_active']
    search_fields = ['tenant__name', 'name']


# ── Planes y suscripciones ────────────────────────────────────────────────────

class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 0


class PlanLimitInline(admin.TabularInline):
    model = PlanLimit
    extra = 0


@admin.register(Plan, site=platform_admin_site)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'price_monthly', 'currency', 'is_public', 'is_active', 'sort']
    list_editable = ['sort']
    inlines = [PlanFeatureInline, PlanLimitInline]

    def has_delete_permission(self, request, obj=None):
        return False  # se desactivan, no se borran (hay suscripciones que los referencian)


@admin.register(Subscription, site=platform_admin_site)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'plan', 'status', 'trial_ends_at', 'current_period_end']
    list_filter = ['status', 'plan']
    search_fields = ['tenant__name', 'tenant__slug']
    readonly_fields = ['tenant', 'updated_at']

    def has_add_permission(self, request):
        return False  # se crean al dar de alta la empresa

    def has_delete_permission(self, request, obj=None):
        return False


# ── Seguridad ────────────────────────────────────────────────────────────────

@admin.register(SecurityEvent, site=platform_admin_site)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'kind', 'email', 'tenant_id_snapshot', 'ip']
    list_filter = ['kind']
    search_fields = ['email', 'ip']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
