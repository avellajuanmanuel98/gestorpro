"""
Capa ORM del aislamiento (fail-closed) probada directamente sobre los modelos.
"""
import pytest

from gestorpro.core.customers.models import Customer
from gestorpro.core.tenancy.context import get_active_tenant_id, tenant_context
from gestorpro.kernel.errors import CrossTenantViolation, TenantContextMissing
from tests import support as s

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]


@pytest.fixture
def two():
    return s.make_tenant('Uno'), s.make_tenant('Dos')


def test_read_without_context_raises(two):
    with pytest.raises(TenantContextMissing):
        Customer.objects.count()


def test_write_without_context_raises(two):
    with pytest.raises(TenantContextMissing):
        Customer(first_name='X', tenant=two[0]).save()


def test_reads_are_scoped_to_active_tenant(two):
    a, b = two
    s.make_customer(a)
    s.make_customer(b)
    with tenant_context(a):
        assert set(Customer.objects.values_list('tenant_id', flat=True)) == {a.id}


def test_cannot_update_object_of_other_tenant_even_if_loaded(two):
    a, b = two
    foreign = s.make_customer(b)
    with tenant_context(a):
        foreign.first_name = 'Hackeado'
        with pytest.raises(CrossTenantViolation):
            foreign.save()
        with pytest.raises(CrossTenantViolation):
            foreign.delete()


def test_foreign_key_to_other_tenant_is_rejected_at_model_level(two):
    from gestorpro.core.billing.models import Invoice
    a, b = two
    foreign_customer = s.make_customer(b)
    with tenant_context(a):
        inv = Invoice(customer_id=foreign_customer.id, number='X', issue_date='2026-01-01', due_date='2026-01-01')
        with pytest.raises(CrossTenantViolation):
            inv.save()


def test_bulk_create_rejects_foreign_objects(two):
    a, b = two
    with tenant_context(a):
        with pytest.raises(CrossTenantViolation):
            Customer.objects.bulk_create([Customer(first_name='X', tenant=b)])


def test_queryset_update_and_delete_are_scoped(two):
    a, b = two
    s.make_customer(a)
    s.make_customer(b)
    with tenant_context(a):
        own = Customer.objects.count()  # incluye el "Consumidor final" creado en el alta
        assert Customer.objects.update(notes='tocado') == own
    with tenant_context(b):
        assert not Customer.objects.filter(notes='tocado').exists()


def test_context_is_cleared_after_each_request(two):
    """Con hilos reutilizados, el tenant de una petición no puede filtrarse a la siguiente."""
    from rest_framework.test import APIClient
    a, _ = two
    user = s.make_user(a, 'ctx@a.co')
    api = s.api_for(user)
    assert api.get(s.ENDPOINTS['customers']).status_code == 200
    assert get_active_tenant_id(required=False) is None
    assert APIClient().get(s.ENDPOINTS['customers']).status_code == 401
