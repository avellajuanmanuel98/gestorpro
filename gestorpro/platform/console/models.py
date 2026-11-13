"""
Bitácora de la PLATAFORMA: todo lo que el personal de GestorPro hace sobre las
empresas (planes, estados, invitaciones, accesos de soporte). Inmutable.
Las acciones que afectan a una empresa además se registran en SU auditoría.
"""
from django.conf import settings
from django.db import models


class PlatformEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    actor_label = models.CharField(max_length=254)
    action = models.CharField(max_length=60)
    tenant = models.ForeignKey('tenancy.Tenant', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    summary = models.CharField(max_length=300)
    details = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['tenant', '-created_at']), models.Index(fields=['action'])]

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.actor_label} {self.action}'

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError('La bitácora de plataforma es inmutable.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('La bitácora de plataforma es inmutable.')
