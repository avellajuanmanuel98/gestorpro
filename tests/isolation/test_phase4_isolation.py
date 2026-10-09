"""Aislamiento de los endpoints de la Fase 4 (auditoría, usuarios, roles, invitaciones)."""
import pytest

from gestorpro.core.access.models import Membership, Role
from gestorpro.core.tenancy.context import tenant_context
from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]


@pytest.fixture
def two():
    a, b = s.make_tenant('Org A'), s.make_tenant('Org B')
    admin_a = s.make_user(a, 'adm@a.co', 'ADMIN')
    s.make_user(b, 'adm@b.co', 'ADMIN')
    with tenant_context(b):
        member_b = Membership.objects.get(user__email='adm@b.co')
        role_b = Role.objects.get(code='CASHIER')
    return {'a': a, 'b': b, 'api': s.api_for(admin_a), 'member_b': member_b, 'role_b': role_b}


def test_audit_log_only_shows_own_company(two):
    s.api_for(s.make_user(two['b'], 'otro@b.co', 'ADMIN'))  # genera eventos en B
    rows = two['api'].get('/api/audit/', {'page_size': 100}).data['results']
    assert rows and all('@b.co' not in r['actor_label'] for r in rows)


def test_members_of_other_company_are_invisible_and_untouchable(two):
    emails = {m['email'] for m in two['api'].get('/api/access/members/').data['results']}
    assert 'adm@b.co' not in emails
    url = f"/api/access/members/{two['member_b'].id}/"
    assert two['api'].patch(url, {'status': 'suspended'}, format='json').status_code == 404
    assert two['api'].delete(url).status_code == 404


def test_cannot_assign_or_invite_with_role_of_other_company(two):
    res = two['api'].post('/api/access/invitations/', {'email': 'x@x.co', 'role': two['role_b'].id}, format='json')
    assert res.status_code == 400
    own = Membership.all_tenants.get(user__email='adm@a.co')
    res = two['api'].patch(f'/api/access/members/{own.id}/', {'role': two['role_b'].id}, format='json')
    assert res.status_code in (400, 403)


def test_roles_of_other_company_are_invisible(two):
    ids = {r['id'] for r in two['api'].get('/api/access/roles/').data}
    assert two['role_b'].id not in ids
    assert two['api'].patch(f"/api/access/roles/{two['role_b'].id}/", {'permissions': []},
                            format='json').status_code == 404
