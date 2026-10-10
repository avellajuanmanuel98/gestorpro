"""Aislamiento de inventario, compras, recetas, producción y mermas."""
import pytest

from gestorpro.capabilities.waste.models import WasteReason
from gestorpro.core.tenancy.context import tenant_context
from gestorpro.core.tenancy.models import Location
from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]


@pytest.fixture
def two():
    a, b = s.make_tenant('Inv A'), s.make_tenant('Inv B')
    api_a = s.api_for(s.make_user(a, 'adm@inva.co', 'ADMIN'))
    api_b = s.api_for(s.make_user(b, 'adm@invb.co', 'ADMIN'))

    def ingredient(api, name):
        return api.post('/api/catalog/items/', {'name': name, 'kind': 'raw_material', 'unit': 'kg',
                                                'avg_cost': '1000', 'stock': '10'}, format='json').data['id']

    def product(api, name):
        return api.post('/api/catalog/items/', {'name': name, 'kind': 'finished_good', 'price': '2000'},
                        format='json').data['id']

    flour_a, flour_b = ingredient(api_a, 'Harina A'), ingredient(api_b, 'Harina B')
    bread_a, bread_b = product(api_a, 'Pan A'), product(api_b, 'Pan B')
    recipe_b = api_b.post('/api/production/recipes/', {'product': bread_b, 'yield_quantity': '10', 'lines': [
        {'ingredient': flour_b, 'quantity': '1'}]}, format='json').data
    batch_b = api_b.post('/api/production/batches/', {'recipe': recipe_b['id'], 'quantity': '10'},
                         format='json').data
    purchase_b = api_b.post('/api/purchases/', {'received_on': '2026-10-10', 'lines': [
        {'item': flour_b, 'quantity': '1', 'unit_cost': '1000'}]}, format='json').data
    with tenant_context(b):
        reason_b = WasteReason.objects.first()
        location_b = Location.objects.get()
    api_b.post('/api/waste/', {'item': flour_b, 'quantity': '1', 'reason': reason_b.id}, format='json')
    return locals()


def test_nothing_from_another_company_is_listed(two):
    api = two['api_a']
    for url in ('/api/purchases/', '/api/production/recipes/', '/api/production/batches/', '/api/waste/'):
        assert api.get(url).data['count'] == 0, url
    names = {m['item_name'] for m in api.get('/api/inventory/movements/', {'page_size': 100}).data['results']}
    assert names and all(name.endswith(' A') for name in names)
    assert api.get(f"/api/purchases/{two['purchase_b']['id']}/").status_code == 404
    assert api.get(f"/api/production/recipes/{two['recipe_b']['id']}/").status_code == 404
    assert api.get('/api/inventory/movements/', {'item': two['flour_b']}).data['count'] == 0


def test_documents_cannot_use_items_or_records_of_another_company(two):
    api, flour_a, flour_b = two['api_a'], two['flour_a'], two['flour_b']
    assert api.post('/api/purchases/', {'received_on': '2026-10-10', 'lines': [
        {'item': flour_b, 'quantity': '1', 'unit_cost': '1'}]}, format='json').status_code == 400
    assert api.post('/api/production/recipes/', {'product': two['bread_a'], 'yield_quantity': '1', 'lines': [
        {'ingredient': flour_b, 'quantity': '1'}]}, format='json').status_code == 400
    assert api.post('/api/production/recipes/', {'product': two['bread_b'], 'yield_quantity': '1', 'lines': [
        {'ingredient': flour_a, 'quantity': '1'}]}, format='json').status_code == 400
    assert api.post('/api/production/batches/', {'recipe': two['recipe_b']['id'], 'quantity': '1'},
                    format='json').status_code == 400
    assert api.post('/api/waste/', {'item': flour_b, 'quantity': '1', 'reason': two['reason_b'].id},
                    format='json').status_code == 400
    assert api.post('/api/inventory/counts/', {'counts': [{'item': flour_b, 'counted': '0'}]},
                    format='json').status_code == 400
    assert api.post('/api/inventory/counts/', {'location': two['location_b'].id, 'counts': [
        {'item': flour_a, 'counted': '0'}]}, format='json').status_code == 400
    with tenant_context(two['b']):
        from gestorpro.core.catalog.models import Item
        # 10 iniciales − 1 (producción) + 1 (compra) − 1 (merma): nada de lo que intentó A la cambió
        assert Item.objects.get(pk=flour_b).stock == 9
