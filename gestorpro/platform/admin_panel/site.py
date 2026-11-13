"""
Admin de Django como consola interna de la PLATAFORMA (personal de GestorPro).

- Solo entra quien tiene `is_platform_admin` + `is_staff`, con contraseña Y el código
  de su app autenticadora (verificación en dos pasos).
- Muestra entidades de plataforma (empresas, usuarios, membresías, roles).
  Deliberadamente NO registra datos de negocio de las empresas (clientes,
  facturas, etc.): el soporte que requiera verlos se hará con impersonación
  explícita y auditada (fase de administración SaaS).
- Las empresas no se pueden eliminar desde aquí: se suspenden.
"""
from functools import update_wrapper

from django import forms
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError
from django.db import transaction

from gestorpro.core.audit import services as audit
from gestorpro.core.audit.models import SecurityEvent
from gestorpro.core.identity import lockout, mfa
from gestorpro.core.tenancy.rls import rls_bypass


class PlatformLoginForm(AdminAuthenticationForm):
    """Contraseña + código de la app autenticadora: el admin no es una puerta trasera sin 2FA."""
    code = forms.CharField(label='Código de la app (6 dígitos)', max_length=8,
                           widget=forms.TextInput(attrs={'autocomplete': 'one-time-code', 'inputmode': 'numeric'}))

    def clean(self):
        if lockout.is_locked(self.data.get('username', '')):
            raise ValidationError('Demasiados intentos fallidos. Espera unos minutos.', code='locked')
        try:
            return super().clean()
        except ValidationError:
            audit.security_event(SecurityEvent.Kind.LOGIN_FAILED, email=lockout.normalize(self.data.get('username')))
            raise

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)  # activa y con is_staff
        if not mfa.required_for(user) or not user.totp_secret:
            raise ValidationError('Esta cuenta necesita verificación en dos pasos (manage.py platform_admin).',
                                  code='mfa_not_enrolled')
        with transaction.atomic():
            locked = type(user).objects.select_for_update().get(pk=user.pk)
            accepted = mfa.verify(locked, self.cleaned_data.get('code', ''))
        if not accepted:
            audit.security_event(SecurityEvent.Kind.MFA_FAILED, user=user)
            raise ValidationError('Código incorrecto o ya usado.', code='mfa_invalid')


class PlatformAdminSite(admin.AdminSite):
    login_form = PlatformLoginForm
    login_template = 'admin/platform_login.html'
    site_header = 'GestorPro — Plataforma'
    site_title = 'GestorPro Plataforma'
    index_title = 'Administración global'

    def has_permission(self, request):
        user = request.user
        return bool(user.is_active and user.is_staff and getattr(user, 'is_platform_admin', False))

    def admin_view(self, view, cacheable=False):
        """Las vistas del admin cruzan empresas: acceso global declarado, solo para personal autorizado."""
        protected = super().admin_view(view, cacheable)

        def inner(request, *args, **kwargs):
            if not self.has_permission(request):
                return protected(request, *args, **kwargs)  # redirige al login sin abrir nada
            with rls_bypass():
                return protected(request, *args, **kwargs)

        return update_wrapper(inner, protected)


platform_admin_site = PlatformAdminSite(name='platform_admin')


class UnscopedReadOnlyAdmin(admin.ModelAdmin):
    """Vista global de solo lectura para modelos con tenant."""

    def get_queryset(self, request):
        return self.model.all_tenants.select_related('tenant')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
