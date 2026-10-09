"""Alta de un cliente real por la plataforma (onboard_tenant)."""
import io

import pytest
from django.core.management import CommandError, call_command
from rest_framework.test import APIClient

from gestorpro.core.access.models import Membership
from gestorpro.core.catalog.models import Category
from gestorpro.core.entitlements import for_tenant
from gestorpro.core.tenancy.context import tenant_context
from gestorpro.core.tenancy.models import Tenant

pytestmark = pytest.mark.django_db


def onboard(*args):
    out = io.StringIO()
    call_command('onboard_tenant', *args, stdout=out)
    text = out.getvalue()
    return text, text.split('/invitation/')[1].split()[0]


def test_onboarding_creates_bakery_with_owner_invitation_and_no_demo_data():
    text, token = onboard('Panadería La Favorita', 'dueno@lafavorita.co', '--plan', 'business', '--city', 'Bogotá')
    tenant = Tenant.objects.get(name='Panadería La Favorita')
    assert tenant.vertical == 'bakery' and tenant.city == 'Bogotá'
    assert for_tenant(tenant.id).plan_code == 'business'
    with tenant_context(tenant):
        assert not Membership.objects.exists()  # el dueño aún no aceptó
        assert Category.objects.filter(name='Panes').exists()  # configuración del vertical, sin productos demo
        from gestorpro.core.catalog.models import Item as Product
        assert not Product.objects.exists()

    res = APIClient().post('/api/auth/accept-invitation/', {
        'token': token, 'password': 'Pan-La-Favorita-2026', 'first_name': 'Dueño', 'last_name': 'Favorita',
    }, format='json')
    assert res.status_code == 201
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    me = client.get('/api/auth/me/').data
    assert me['tenant']['name'] == 'Panadería La Favorita' and me['role']['code'] == 'OWNER'


def test_onboarding_rejects_duplicates_and_bad_input():
    onboard('Panadería La Favorita', 'dueno@lafavorita.co')
    with pytest.raises(CommandError):
        onboard('Panadería La Favorita', 'otro@lafavorita.co')
    with pytest.raises(CommandError):
        onboard('Otra', 'no-es-email')


def test_reinvite_generates_new_link_and_revokes_previous():
    _, first = onboard('Panadería La Favorita', 'dueno@lafavorita.co')
    slug = Tenant.objects.get().slug
    _, second = onboard('--reinvite', slug, 'dueno@lafavorita.co')
    assert first != second
    assert APIClient().get(f'/api/auth/invitation/{first}/').status_code == 404
    assert APIClient().get(f'/api/auth/invitation/{second}/').status_code == 200
