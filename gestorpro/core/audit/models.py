"""
Registro de auditoría.

- AuditLog: acciones dentro de una empresa. Lo consultan sus administradores.
- SecurityEvent: eventos de autenticación a nivel plataforma (intentos de
  login fallidos, cambios de contraseña...). Solo lo ve el personal de GestorPro.

Ambos son de solo inserción: el ORM rechaza modificaciones y borrados, y un
trigger de PostgreSQL rechaza cualquier UPDATE (ver migración 0002).
"""
from django.conf import settings
from django.db import models

from gestorpro.core.tenancy.db import TenantManager, TenantModel, TenantQuerySet


class AppendOnlyError(Exception):
    pass


class AppendOnlyQuerySet(TenantQuerySet):
    def update(self, **kwargs):
        raise AppendOnlyError('El registro de auditoría no se puede modificar.')

    def delete(self):
        raise AppendOnlyError('El registro de auditoría no se puede borrar.')


class AuditLogManager(TenantManager.from_queryset(AppendOnlyQuerySet)):
    pass


class AuditLog(TenantModel):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='+')
    actor_label = models.CharField(max_length=254)  # email al momento del hecho
    action = models.CharField(max_length=80)  # p. ej. 'catalog.product.price_changed'
    entity_type = models.CharField(max_length=80, blank=True, default='')
    entity_id = models.CharField(max_length=64, blank=True, default='')
    summary = models.CharField(max_length=300)  # texto legible para la persona
    changes = models.JSONField(default=dict, blank=True)  # {campo: [antes, después]}
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True, default='')

    objects = AuditLogManager()

    class Meta(TenantModel.Meta):
        verbose_name = 'Registro de auditoría'
        verbose_name_plural = 'Registro de auditoría'
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
            models.Index(fields=['tenant', 'action']),
            models.Index(fields=['tenant', 'entity_type', 'entity_id']),
        ]

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.actor_label} {self.action}'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AppendOnlyError('El registro de auditoría no se puede modificar.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AppendOnlyError('El registro de auditoría no se puede borrar.')


class SecurityEvent(models.Model):
    """Eventos de autenticación globales (no pertenecen a una empresa)."""

    class Kind(models.TextChoices):
        LOGIN_SUCCEEDED = 'login_succeeded', 'Inicio de sesión'
        LOGIN_FAILED = 'login_failed', 'Inicio de sesión fallido'
        LOGOUT = 'logout', 'Cierre de sesión'
        PASSWORD_CHANGED = 'password_changed', 'Cambio de contraseña'
        TENANT_SWITCHED = 'tenant_switched', 'Cambio de empresa'
        INVITATION_ACCEPTED = 'invitation_accepted', 'Invitación aceptada'

    kind = models.CharField(max_length=30, choices=Kind.choices)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='+')
    email = models.CharField(max_length=254, blank=True, default='')
    tenant_id_snapshot = models.BigIntegerField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Evento de seguridad'
        verbose_name_plural = 'Eventos de seguridad'
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['kind', '-created_at']), models.Index(fields=['email', '-created_at'])]

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.kind} {self.email}'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AppendOnlyError('Los eventos de seguridad no se pueden modificar.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AppendOnlyError('Los eventos de seguridad no se pueden borrar.')
