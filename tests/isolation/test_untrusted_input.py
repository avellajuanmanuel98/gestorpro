"""Valores críticos enviados por el frontend no son confiables."""
from decimal import Decimal

import pytest

from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]


def test_invoice_price_comes_from_catalog_not_from_client(world):
    """Un usuario sin permiso de cambiar precios no puede facturar a $1 un producto de $1.000."""
    api = s.api_for(world['cashier_a'])
    res = api.post(s.ENDPOINTS['invoices'],
                   s.invoice_payload(world['customer_a'].id, world['product_a'].id, unit_price='1'),
                   format='json')
    if res.status_code == 403:
        return  # tampoco puede facturar: aceptable
    assert res.status_code in (201, 400), res.content
    if res.status_code == 201:
        assert Decimal(str(res.data['items'][0]['unit_price'])) == world['product_a'].price


def test_money_is_serialized_without_float_precision_loss(world):
    api = s.api_for(world['admin_b'])
    res = api.get(s.ENDPOINTS['billing_summary'])
    assert isinstance(res.data['paid_total'], str), type(res.data['paid_total'])
