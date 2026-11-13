"""
Fase 11: el recorrido crítico de un día, de punta a punta en el navegador:

    cajero abre caja → vende → cierra caja cuadrada
    → la dueña ve la existencia descontada en el libro de inventario
    → y la venta en el tablero de Inicio, con las cifras exactas.
"""
import re
from decimal import Decimal

import pytest
from django.db import transaction

from gestorpro.core.access.models import Membership
from gestorpro.core.cash.models import CashSession
from gestorpro.core.catalog.models import Item, UnitOfMeasure
from gestorpro.core.inventory import services as inventory
from gestorpro.core.inventory.models import StockMovement
from gestorpro.core.sales.models import Sale
from gestorpro.core.tenancy.context import tenant_context
from tests import support as s

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True, serialized_rollback=True)]


@pytest.fixture
def bakery():
    t = s.make_tenant('Panaderia E2E')  # el correo del dueño sale del nombre: sin tildes
    cashier = s.make_user(t, 'cajero@e2e.co', 'CASHIER')
    with tenant_context(t), transaction.atomic():
        owner = Membership.objects.get(role__code='OWNER').user
        pan = Item.objects.create(name='Pan de bono', code='PAN-001', price=Decimal('2000'), tax_rate=Decimal('0'),
                                  unit=UnitOfMeasure.objects.get(code='und'))
        # 20 panes de saldo inicial, por el libro como en la vida real
        inventory.post(item=inventory.lock_items([pan.id])[pan.id], location=inventory.default_location(),
                       type=StockMovement.Type.OPENING, quantity='20', unit_cost='700', user=owner,
                       source=inventory.Source('item', pan.id, 'Alta del ítem'))
    return {'t': t, 'cashier': cashier, 'owner': owner, 'pan': pan}


def login(page, email):
    page.goto('/login')
    page.get_by_label('Email').fill(email)
    page.get_by_label('Contraseña').first.fill(s.PASSWORD)
    page.get_by_role('button', name='Entrar').click()


def test_a_day_from_the_register_to_the_dashboard(bakery, new_page):
    from playwright.sync_api import expect  # solo si Playwright está instalado

    # 1. El cajero entra directo al POS y abre su caja
    page = new_page()
    login(page, 'cajero@e2e.co')
    page.wait_for_url('**/pos')
    page.get_by_label('Base inicial en efectivo').fill('100000')
    page.get_by_role('button', name='Abrir caja').click()

    # 2. Vende 3 panes de bono en efectivo
    for _ in range(3):
        page.get_by_role('button', name=re.compile('Pan de bono')).first.click()
    page.get_by_role('button', name=re.compile('^Cobrar')).click()
    page.get_by_role('button', name='Confirmar pago').click()
    dialog = page.get_by_role('dialog', name='Venta registrada')
    dialog.wait_for()
    dialog.get_by_role('button', name='Nueva venta').click()

    with tenant_context(bakery['t']):
        sale = Sale.objects.get()
        assert sale.total == Decimal('6000') and sale.lines.get().unit_price == Decimal('2000')

    # 3. Cierra la caja contando 1 × $100.000 y 3 × $2.000: cuadra exacto
    page.goto('/cash')
    page.get_by_role('button', name='Cerrar caja').first.click()
    close = page.get_by_role('dialog')
    close.get_by_label('Cantidad de $ 100.000').fill('1')
    close.get_by_label('Cantidad de $ 2.000').fill('3')
    close.get_by_role('button', name='Cerrar caja').click()
    close.wait_for(state='detached')

    with tenant_context(bakery['t']):
        session = CashSession.objects.get()
        assert session.status == CashSession.Status.CLOSED
        assert session.expected_amount == session.counted_amount == Decimal('106000')
        assert session.difference == 0

    # 4. La dueña ve la salida en el libro de inventario, con el saldo correcto
    owner = new_page()
    login(owner, bakery['owner'].email)
    owner.wait_for_url('**/dashboard')
    owner.goto('/movements')
    row = owner.locator('tr', has_text=f'Venta {sale.number}')
    row.wait_for()
    assert '17' in row.inner_text()  # 20 iniciales − 3 vendidos

    with tenant_context(bakery['t']):
        assert Item.objects.get(pk=bakery['pan'].pk).stock == Decimal('17')

    # 5. Y el tablero muestra exactamente esa venta: $ 6.000 en 1 transacción, ticket de $ 6.000
    owner.goto('/dashboard')
    expect(kpi(owner, 'Ventas hoy')).to_have_text(re.compile(r'^\$\s6\.000$'))
    expect(kpi(owner, 'Transacciones')).to_have_text('1')
    expect(kpi(owner, 'Ticket promedio')).to_have_text(re.compile(r'^\$\s6\.000$'))


def kpi(page, label):
    """El valor de la tarjeta KPI cuyo rótulo es exactamente `label`."""
    return page.locator('p', has_text=re.compile(f'^{label}$')).locator('xpath=following-sibling::p[1]')
