"""
Caja: cajas registradoras, turnos (sesiones) y movimientos de efectivo.

    CashRegister ─< CashSession ─< CashMovement

- Una caja pertenece a una sucursal. En cada caja solo puede haber un turno
  abierto, y cada persona solo puede tener un turno abierto a la vez.
- Todo lo que entra o sale del cajón es un CashMovement con signo: ventas en
  efectivo (+), anulaciones (−), ingresos (+), gastos (−) y retiros (−).
  Nunca se editan ni se borran: una corrección es un movimiento nuevo.
- Al cerrar: esperado = base inicial + Σ movimientos; la diferencia con lo
  contado queda registrada, explicada y auditada.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

from gestorpro.core.tenancy.db import TenantModel


class CashRegister(TenantModel):
    location = models.ForeignKey('tenancy.Location', verbose_name='sucursal', on_delete=models.PROTECT,
                                 related_name='+')
    name = models.CharField(verbose_name='nombre', max_length=80)
    is_active = models.BooleanField(verbose_name='activa', default=True)

    class Meta(TenantModel.Meta):
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'
        ordering = ['name']
        constraints = [models.UniqueConstraint(fields=['tenant', 'location', 'name'], name='register_unique_name')]

    def __str__(self):
        return self.name


class CashSession(TenantModel):

    class Status(models.TextChoices):
        OPEN = 'open', 'Abierta'
        CLOSED = 'closed', 'Cerrada'

    register = models.ForeignKey(CashRegister, verbose_name='caja', on_delete=models.PROTECT, related_name='sessions')
    status = models.CharField(verbose_name='estado', max_length=10, choices=Status.choices, default=Status.OPEN)
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    opened_at = models.DateTimeField(auto_now_add=True)
    opening_amount = models.DecimalField(verbose_name='base inicial', max_digits=14, decimal_places=2)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                  related_name='+')
    closed_at = models.DateTimeField(null=True, blank=True)
    expected_amount = models.DecimalField(verbose_name='esperado', max_digits=14, decimal_places=2, null=True,
                                          blank=True)
    counted_amount = models.DecimalField(verbose_name='contado', max_digits=14, decimal_places=2, null=True,
                                         blank=True)
    difference = models.DecimalField(verbose_name='diferencia', max_digits=14, decimal_places=2, null=True,
                                     blank=True)
    denominations = models.JSONField(verbose_name='conteo por denominación', default=dict, blank=True)
    closing_note = models.TextField(verbose_name='observación de cierre', blank=True, default='')

    class Meta(TenantModel.Meta):
        verbose_name = 'Turno de caja'
        verbose_name_plural = 'Turnos de caja'
        ordering = ['-opened_at']
        constraints = [
            models.UniqueConstraint(fields=['register'], condition=Q(status='open'),
                                    name='cash_one_open_session_per_register',
                                    violation_error_message='Esta caja ya tiene un turno abierto.'),
            models.UniqueConstraint(fields=['tenant', 'opened_by'], condition=Q(status='open'),
                                    name='cash_one_open_session_per_user',
                                    violation_error_message='Ya tienes un turno de caja abierto.'),
        ]
        indexes = [models.Index(fields=['tenant', 'status'])]

    def __str__(self):
        return f'{self.register} · {self.opened_at:%Y-%m-%d %H:%M}'

    @property
    def is_open(self):
        return self.status == self.Status.OPEN


class CashMovement(TenantModel):

    class Type(models.TextChoices):
        SALE = 'sale', 'Venta'
        VOID = 'void', 'Anulación de venta'
        INCOME = 'income', 'Ingreso'
        EXPENSE = 'expense', 'Gasto'
        WITHDRAWAL = 'withdrawal', 'Retiro'

    # Tipos que el usuario registra a mano (los demás los genera el sistema)
    MANUAL_TYPES = (Type.INCOME, Type.EXPENSE, Type.WITHDRAWAL)
    OUTFLOW_TYPES = (Type.VOID, Type.EXPENSE, Type.WITHDRAWAL)

    session = models.ForeignKey(CashSession, on_delete=models.PROTECT, related_name='movements')
    type = models.CharField(verbose_name='tipo', max_length=12, choices=Type.choices)
    amount = models.DecimalField(verbose_name='valor', max_digits=14, decimal_places=2,
                                 help_text='Con signo: positivo entra al cajón, negativo sale.')
    reason = models.CharField(verbose_name='motivo', max_length=200, blank=True, default='')
    sale = models.ForeignKey('sales.Sale', on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')

    class Meta(TenantModel.Meta):
        verbose_name = 'Movimiento de caja'
        verbose_name_plural = 'Movimientos de caja'
        ordering = ['created_at', 'id']
        constraints = [
            models.CheckConstraint(
                condition=(Q(type__in=['sale', 'income'], amount__gt=0)
                           | Q(type__in=['void', 'expense', 'withdrawal'], amount__lt=0)),
                name='cash_movement_sign_matches_type'),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError('Los movimientos de caja no se modifican; registra uno nuevo.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Los movimientos de caja no se borran.')
