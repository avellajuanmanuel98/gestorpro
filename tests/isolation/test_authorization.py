"""S5: los permisos se validan en backend, por rol."""
import pytest

from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]


def test_restricted_role_cannot_delete_invoices(world):
    from tests.support import make_invoice
    inv = make_invoice(world['a'], world['customer_a'], world['product_a'])
    api = s.api_for(world['cashier_a'])
    res = api.delete(f"{s.ENDPOINTS['invoices']}{inv.id}/")
    assert res.status_code == 403


def test_restricted_role_cannot_see_salaries(world):
    api = s.api_for(world['cashier_a'])
    res = api.get(f"{s.ENDPOINTS['employees']}{world['employee_a'].id}/")
    assert res.status_code == 403 or 'salary' not in res.data


def test_restricted_role_cannot_manage_catalog(world):
    api = s.api_for(world['cashier_a'])
    res = api.patch(f"{s.ENDPOINTS['products']}{world['product_a'].id}/", {'price': '1'}, format='json')
    assert res.status_code == 403
