"""
Diferencia grande al cerrar: el cajero no puede cerrar solo (supera la tolerancia), y la dueña
cierra ese turno abierto desde Caja → Historial. Antes el servidor lo permitía pero la pantalla
no tenía el botón, y el turno quedaba sin poder cerrarse.
"""
import re
from decimal import Decimal

import pytest

from gestorpro.core.cash.models import CashSession
from gestorpro.core.tenancy.context import tenant_context
from tests.e2e.test_sale_to_report import bakery, login  # noqa: F401  (fixture compartida)

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True, serialized_rollback=True)]


def test_owner_closes_a_cashier_shift_with_a_big_difference(bakery, new_page):  # noqa: F811
    from playwright.sync_api import expect

    # El cajero abre con $100.000, vende $6.000 y cuenta solo $50.000 (faltan $56.000)
    page = new_page()
    login(page, 'cajero@e2e.co')
    page.wait_for_url('**/pos')
    page.get_by_label('Base inicial en efectivo').fill('100000')
    page.get_by_role('button', name='Abrir caja').click()
    for _ in range(3):
        page.get_by_role('button', name=re.compile('Pan de bono')).first.click()
    page.get_by_role('button', name=re.compile('^Cobrar')).click()
    page.get_by_role('dialog', name='Cobrar').get_by_role('button', name='Confirmar pago').click()
    page.get_by_role('dialog', name='Venta registrada').get_by_role('button', name='Nueva venta').click()

    page.goto('/cash')
    page.get_by_role('button', name='Cerrar caja').first.click()
    close = page.get_by_role('dialog')
    close.get_by_label('Cantidad de $ 50.000').fill('1')
    close.get_by_label(re.compile('Qué pasó')).fill('Faltante sin explicar')
    expect(close.get_by_text(re.compile('Caja → Historial'))).to_be_visible()   # le dice cómo seguir
    expect(close.get_by_role('button', name='Cerrar caja')).to_be_disabled()

    # La dueña lo cierra desde el historial
    owner = new_page()
    login(owner, bakery['owner'].email)
    owner.wait_for_url('**/dashboard')
    owner.goto('/cash')
    owner.get_by_role('tab', name=re.compile('Historial')).click()
    owner.get_by_role('cell', name=re.compile('Caja principal')).first.click()
    detail = owner.get_by_role('dialog')
    detail.get_by_role('button', name='Cerrar este turno').click()
    detail.get_by_label('Cantidad de $ 50.000').fill('1')
    detail.get_by_label(re.compile('Qué pasó')).fill('Faltante revisado con la cajera')
    detail.get_by_role('button', name='Cerrar caja').click()
    detail.wait_for(state='detached')

    with tenant_context(bakery['t']):
        session = CashSession.objects.get()
        assert session.status == CashSession.Status.CLOSED
        assert session.difference == Decimal('-56000') and session.closed_by == bakery['owner']
