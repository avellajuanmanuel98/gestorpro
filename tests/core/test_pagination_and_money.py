from decimal import Decimal

import pytest

from gestorpro.core.tenancy.context import tenant_context
from gestorpro.kernel.money import money, money_str, percentage_of
from tests import support as s


def test_money_rounding_is_half_up():
    assert money('0.005') == Decimal('0.01')
    assert money('2.675') == Decimal('2.68')  # con float sería 2.67
    assert percentage_of('1000', '19') == Decimal('190.00')
    assert money_str(None) == '0.00'


def test_money_rejects_float():
    with pytest.raises(TypeError):
        money(0.1)


@pytest.mark.django_db
def test_pagination_exposes_real_totals():
    from gestorpro.core.customers.models import Customer
    t = s.make_tenant('Muchos')
    with tenant_context(t):
        Customer.objects.bulk_create([Customer(first_name=f'C{i:03}') for i in range(45)])
    api = s.api_for(s.make_user(t, 'p@m.co'))
    page = api.get(s.ENDPOINTS['customers']).data
    assert page['count'] == 45 and page['total_pages'] == 3 and len(page['results']) == 20
    last = api.get(s.ENDPOINTS['customers'], {'page': 3}).data
    assert len(last['results']) == 5
    capped = api.get(s.ENDPOINTS['customers'], {'page_size': 1000}).data
    assert capped['page_size'] == 100
