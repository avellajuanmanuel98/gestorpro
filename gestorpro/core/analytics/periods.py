"""
Períodos de análisis y su período COMPARABLE, en la zona horaria de la empresa.

    today       hoy                 vs el mismo día de la semana pasada (un sábado
                                    se compara con un sábado, no con el viernes)
    yesterday   ayer                vs el mismo día de la semana anterior
    7d / 30d    últimos N días      vs los N días anteriores
    this_month  mes a la fecha      vs el mes anterior hasta el mismo día
    last_month  mes anterior        vs el mes previo completo
    this_year   año a la fecha      vs el año anterior hasta la misma fecha
    custom      [desde, hasta]      vs el mismo número de días inmediatamente antes

Los rangos son semiabiertos [inicio, fin) en datetimes con zona horaria.
"""
import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework.exceptions import ValidationError

PRESETS = ('today', 'yesterday', '7d', '30d', 'this_month', 'last_month', 'this_year', 'custom')
MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
WEEKDAYS = ['lun', 'mar', 'mié', 'jue', 'vie', 'sáb', 'dom']


@dataclass(frozen=True)
class Range:
    first: date   # primer día incluido
    last: date    # último día incluido
    tz: ZoneInfo

    @property
    def start(self) -> datetime:
        return datetime.combine(self.first, time.min, tzinfo=self.tz)

    @property
    def end(self) -> datetime:
        return datetime.combine(self.last + timedelta(days=1), time.min, tzinfo=self.tz)

    @property
    def days(self) -> int:
        return (self.last - self.first).days + 1

    def label(self) -> str:
        fmt = lambda d: f'{WEEKDAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]}'  # noqa: E731
        return fmt(self.first) if self.first == self.last else f'{fmt(self.first)} – {fmt(self.last)}'


@dataclass(frozen=True)
class Period:
    preset: str
    current: Range
    previous: Range

    def as_dict(self) -> dict:
        return {'preset': self.preset, 'from': self.current.first.isoformat(), 'to': self.current.last.isoformat(),
                'label': self.current.label(), 'days': self.current.days,
                'previous': {'from': self.previous.first.isoformat(), 'to': self.previous.last.isoformat(),
                             'label': self.previous.label()}}


def _shift_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year, month = d.year + month // 12, month % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def resolve(tenant, preset: str = 'today', date_from: str | None = None, date_to: str | None = None,
            today: date | None = None) -> Period:
    if preset not in PRESETS:
        raise ValidationError({'period': f'Período desconocido. Usa uno de: {", ".join(PRESETS)}.'})
    tz = ZoneInfo(tenant.timezone)
    today = today or timezone.now().astimezone(tz).date()
    week = timedelta(days=7)

    if preset == 'today':
        cur = (today, today)
        prev = (today - week, today - week)
    elif preset == 'yesterday':
        y = today - timedelta(days=1)
        cur, prev = (y, y), (y - week, y - week)
    elif preset in ('7d', '30d'):
        n = 7 if preset == '7d' else 30
        cur = (today - timedelta(days=n - 1), today)
        prev = (cur[0] - timedelta(days=n), cur[0] - timedelta(days=1))
    elif preset == 'this_month':
        cur = (today.replace(day=1), today)
        p_first = _shift_months(cur[0], -1)
        prev = (p_first, min(_shift_months(today, -1), cur[0] - timedelta(days=1)))
    elif preset == 'last_month':
        first = _shift_months(today.replace(day=1), -1)
        cur = (first, today.replace(day=1) - timedelta(days=1))
        p_first = _shift_months(first, -1)
        prev = (p_first, first - timedelta(days=1))
    elif preset == 'this_year':
        cur = (date(today.year, 1, 1), today)
        last_year = today.replace(year=today.year - 1) if not (today.month == 2 and today.day == 29) \
            else date(today.year - 1, 2, 28)
        prev = (date(today.year - 1, 1, 1), last_year)
    else:
        try:
            first = datetime.strptime(date_from or '', '%Y-%m-%d').date()
            last = datetime.strptime(date_to or '', '%Y-%m-%d').date()
        except ValueError as exc:
            raise ValidationError({'period': 'Indica desde y hasta con formato AAAA-MM-DD.'}) from exc
        if last < first or (last - first).days > 731:
            raise ValidationError({'period': 'Rango inválido (máximo 2 años).'})
        cur = (first, last)
        n = (last - first).days + 1
        prev = (first - timedelta(days=n), first - timedelta(days=1))
    return Period(preset, Range(*cur, tz), Range(*prev, tz))


def change_pct(current, previous):
    """Variación porcentual. None si no hay base de comparación (nunca un número inventado)."""
    if previous is None or previous == 0 or current is None:
        return None
    return round(float((current - previous) / abs(previous) * 100), 1)
