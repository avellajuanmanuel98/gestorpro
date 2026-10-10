"""
Servicio de caja. Reglas que garantiza el backend:

- Solo se abre un turno por caja y uno por persona a la vez.
- Ingresos, gastos y retiros exigen motivo; los gastos y retiros no pueden
  dejar el cajón en negativo según lo esperado.
- Esperado = base inicial + Σ movimientos (todos con signo). Solo el efectivo
  pasa por el cajón; tarjeta y transferencias se concilian aparte.
- Cerrar con diferencia exige una explicación; si la diferencia supera
  CASH_DIFFERENCE_TOLERANCE, además el permiso `cash.manage` (supervisor).
- Cerrar el turno de otra persona exige `cash.manage`.
- Todo queda auditado.
"""
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from gestorpro.core.audit import services as audit
from gestorpro.kernel.money import ZERO, money, money_str

from .models import CashMovement, CashRegister, CashSession

# Billetes y monedas en circulación en Colombia (para el conteo del cierre)
DENOMINATIONS = [100000, 50000, 20000, 10000, 5000, 2000, 1000, 500, 200, 100, 50]


def tolerance() -> Decimal:
    return money(getattr(settings, 'CASH_DIFFERENCE_TOLERANCE', '5000'))


def current_session(user) -> CashSession | None:
    return CashSession.objects.select_related('register').filter(opened_by=user, status=CashSession.Status.OPEN).first()


def movements_total(session: CashSession) -> Decimal:
    return session.movements.aggregate(t=Sum('amount'))['t'] or ZERO


def expected_amount(session: CashSession) -> Decimal:
    return money(session.opening_amount + movements_total(session))


@transaction.atomic
def open_session(*, user, register: CashRegister, opening_amount) -> CashSession:
    amount = money(opening_amount)
    if amount < 0:
        raise ValidationError({'opening_amount': 'La base no puede ser negativa.'})
    if not register.is_active:
        raise ValidationError({'register': 'Esta caja está inactiva.'})
    if current_session(user) is not None:
        raise ValidationError('Ya tienes un turno de caja abierto.')
    if CashSession.objects.filter(register=register, status=CashSession.Status.OPEN).exists():
        raise ValidationError({'register': 'Esta caja ya tiene un turno abierto por otra persona.'})
    try:
        with transaction.atomic():
            session = CashSession.objects.create(register=register, opened_by=user, opening_amount=amount)
    except IntegrityError as exc:  # dos aperturas simultáneas: gana una
        raise ValidationError('La caja acaba de abrirse desde otro equipo.') from exc
    audit.record('cash.session.opened', target=session,
                 summary=f'Abrió {register.name} con base de ${money_str(amount)}')
    return session


def _locked_open_session(session: CashSession) -> CashSession:
    session = CashSession.objects.select_for_update().get(pk=session.pk)
    if not session.is_open:
        raise ValidationError('El turno de caja ya está cerrado.')
    return session


def _assert_can_operate(membership, session: CashSession):
    if session.opened_by_id != membership.user_id and not membership.has_perm('cash.manage'):
        raise PermissionDenied('Este turno de caja pertenece a otra persona.')


@transaction.atomic
def add_movement(*, membership, session: CashSession, type: str, amount, reason: str) -> CashMovement:
    _assert_can_operate(membership, session)
    session = _locked_open_session(session)
    if type not in CashMovement.MANUAL_TYPES:
        raise ValidationError({'type': 'Tipo de movimiento no permitido.'})
    value = money(amount)
    if value <= 0:
        raise ValidationError({'amount': 'Indica un valor mayor que cero.'})
    if not (reason or '').strip():
        raise ValidationError({'reason': 'Indica el motivo.'})
    signed = -value if type in CashMovement.OUTFLOW_TYPES else value
    if signed < 0 and expected_amount(session) + signed < 0:
        raise ValidationError({'amount': 'No hay suficiente efectivo esperado en la caja para ese valor.'})
    movement = CashMovement.objects.create(session=session, type=type, amount=signed, reason=reason.strip(),
                                           created_by=membership.user)
    label = dict(CashMovement.Type.choices)[type]
    audit.record(f'cash.movement.{type}', target=session,
                 summary=f'{label} de ${money_str(value)} en {session.register.name}: {reason.strip()}')
    return movement


@transaction.atomic
def close_session(*, membership, session: CashSession, counted_amount, denominations: dict | None = None,
                  note: str = '') -> CashSession:
    _assert_can_operate(membership, session)
    session = _locked_open_session(session)
    counted = money(counted_amount)
    if counted < 0:
        raise ValidationError({'counted_amount': 'El conteo no puede ser negativo.'})
    clean_denoms = {}
    for key, qty in (denominations or {}).items():
        if int(key) not in DENOMINATIONS or int(qty) < 0:
            raise ValidationError({'denominations': f'Denominación inválida: {key}.'})
        if int(qty):
            clean_denoms[str(int(key))] = int(qty)
    if clean_denoms and money(sum(int(k) * q for k, q in clean_denoms.items())) != counted:
        raise ValidationError({'counted_amount': 'El total no coincide con el conteo por denominación.'})

    expected = expected_amount(session)
    difference = counted - expected
    note = (note or '').strip()
    if difference != 0 and not note:
        raise ValidationError({'note': 'Hay una diferencia: explica qué pasó antes de cerrar.'})
    if abs(difference) > tolerance() and not membership.has_perm('cash.manage'):
        raise PermissionDenied(f'La diferencia supera ${money_str(tolerance())}: debe cerrarla un supervisor.')

    session.status = CashSession.Status.CLOSED
    session.closed_by = membership.user
    session.closed_at = timezone.now()
    session.expected_amount, session.counted_amount, session.difference = expected, counted, difference
    session.denominations, session.closing_note = clean_denoms, note
    session.save()
    detail = 'sin diferencia' if difference == 0 else f'diferencia ${money_str(difference)}'
    audit.record('cash.session.closed', target=session,
                 summary=f'Cerró {session.register.name}: esperado ${money_str(expected)}, '
                         f'contado ${money_str(counted)} ({detail})',
                 changes={'difference': [None, money_str(difference)]})
    return session
