"""El soporte de la plataforma en la empresa A no ve nada de la empresa B."""
import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]


def test_support_session_is_confined_to_its_company():
    a, b = s.make_tenant('Sop A'), s.make_tenant('Sop B')
    s.make_customer(a)
    foreign = s.make_customer(b)
    staff = s._user('agente@gestorpro.co')
    call_command('platform_admin', staff.email)
    api = s.api_for(staff)
    res = api.post(f'/api/platform/tenants/{a.id}/support/', {'reason': 'Revisar un cliente duplicado'}, format='json')
    sup = APIClient()
    sup.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    names = {c['id'] for c in sup.get('/api/customers/', {'page_size': 100}).data['results']}
    assert foreign.id not in names
    assert sup.get(f'/api/customers/{foreign.id}/').status_code == 404
    assert sup.get('/api/tenant/').data['id'] == a.id
    # Sin token de soporte, el personal de la plataforma no tiene empresa: no ve datos de ninguna
    assert api.get('/api/customers/').status_code == 403
