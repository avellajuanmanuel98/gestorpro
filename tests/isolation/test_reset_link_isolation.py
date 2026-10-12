"""Un administrador no puede generar enlaces de contraseña para personas de otra empresa."""
import pytest

from gestorpro.core.access.models import Membership
from gestorpro.core.tenancy.context import tenant_context
from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]


def test_reset_links_are_confined_to_the_admins_company():
    a, b = s.make_tenant('Clave A'), s.make_tenant('Clave B')
    admin_a = s.api_for(s.make_user(a, 'adm@clavea.co', 'ADMIN'))
    victim = s.make_user(b, 'duena@claveb.co', 'CASHIER')
    with tenant_context(b):
        member_b = Membership.objects.get(user=victim)
    assert admin_a.post(f'/api/access/members/{member_b.id}/reset-link/').status_code == 404
    assert admin_a.post(f'/api/platform/tenants/{b.id}/reset-link/', {'email': victim.email},
                        format='json').status_code == 403
