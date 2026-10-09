"""
Planes y suscripciones (capa Platform).

Las funcionalidades y límites de cada plan son DATOS (PlanFeature, PlanLimit),
editables desde la consola de plataforma, no constantes en el código. Las
claves válidas están en gestorpro.core.entitlements (FEATURES, LIMITS).

Aún no hay cobro real: `price_monthly` puede quedar vacío ("por definir") y
`external_ref` reservará el id de la pasarela de pagos cuando exista.
"""
from django.core.exceptions import ValidationError
from django.db import models

from gestorpro.core import entitlements


class Plan(models.Model):
    code = models.SlugField('código', unique=True)
    name = models.CharField('nombre', max_length=60)
    description = models.CharField('descripción', max_length=200, blank=True, default='')
    price_monthly = models.DecimalField('precio mensual', max_digits=12, decimal_places=2, null=True, blank=True,
                                        help_text='Vacío = por definir.')
    currency = models.CharField('moneda', max_length=3, default='COP')
    is_public = models.BooleanField('visible en la página de precios', default=True)
    is_active = models.BooleanField('activo', default=True)
    sort = models.PositiveSmallIntegerField('orden', default=0)

    class Meta:
        verbose_name = 'Plan'
        verbose_name_plural = 'Planes'
        ordering = ['sort', 'code']

    def __str__(self):
        return self.name


class PlanFeature(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='features')
    key = models.CharField('funcionalidad', max_length=60)

    class Meta:
        verbose_name = 'Funcionalidad del plan'
        verbose_name_plural = 'Funcionalidades del plan'
        constraints = [models.UniqueConstraint(fields=['plan', 'key'], name='planfeature_unique')]

    def __str__(self):
        return self.key

    def clean(self):
        if self.key not in entitlements.FEATURES:
            raise ValidationError({'key': f'Funcionalidad desconocida. Válidas: {", ".join(entitlements.FEATURES)}'})


class PlanLimit(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='limits')
    key = models.CharField('límite', max_length=60)
    value = models.PositiveIntegerField('valor', null=True, blank=True, help_text='Vacío = ilimitado.')

    class Meta:
        verbose_name = 'Límite del plan'
        verbose_name_plural = 'Límites del plan'
        constraints = [models.UniqueConstraint(fields=['plan', 'key'], name='planlimit_unique')]

    def __str__(self):
        return f'{self.key}={self.value if self.value is not None else "∞"}'

    def clean(self):
        if self.key not in entitlements.LIMITS:
            raise ValidationError({'key': f'Límite desconocido. Válidos: {", ".join(entitlements.LIMITS)}'})


class Subscription(models.Model):
    """Suscripción de una empresa. La administra la plataforma; la empresa solo la consulta."""

    class Status(models.TextChoices):
        TRIALING = 'trialing', 'En prueba'
        ACTIVE = 'active', 'Activa'
        PAST_DUE = 'past_due', 'Pago pendiente'
        CANCELED = 'canceled', 'Cancelada'

    tenant = models.OneToOneField('tenancy.Tenant', on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField('estado', max_length=20, choices=Status.choices, default=Status.TRIALING)
    started_at = models.DateTimeField('inicio')
    current_period_end = models.DateTimeField('fin del período / renovación', null=True, blank=True)
    trial_ends_at = models.DateTimeField('fin de la prueba', null=True, blank=True)
    canceled_at = models.DateTimeField('cancelada el', null=True, blank=True)
    external_ref = models.CharField('referencia de la pasarela de pago', max_length=120, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Suscripción'
        verbose_name_plural = 'Suscripciones'

    def __str__(self):
        return f'{self.tenant} — {self.plan} ({self.get_status_display()})'
