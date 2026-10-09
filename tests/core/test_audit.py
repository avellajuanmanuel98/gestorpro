"""Auditoría: qué se registra, inmutabilidad y aislamiento."""
import pytest
from django.db import connection, transaction

from gestorpro.core.audit.models import AppendOnlyError, AuditLog, SecurityEvent
from gestorpro.core.tenancy.context import tenant_context
from tests import support as s

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    t = s.make_tenant('Auditada')
    admin = s.make_user(t, 'admin@aud.co', 'ADMIN')
    return {'t': t, 'admin': admin, 'api': s.api_for(admin)}


def logs(tenant, **filters):
    with tenant_context(tenant):
        return list(AuditLog.objects.filter(**filters).order_by('id'))


def test_login_is_audited_with_actor_and_ip(ctx):
    entry = logs(ctx['t'], action='auth.login')[-1]
    assert entry.actor_id == ctx['admin'].id
    assert entry.actor_label == 'admin@aud.co'
    assert entry.ip == '127.0.0.1'


def test_failed_login_is_a_security_event():
    from rest_framework.test import APIClient
    APIClient().post(s.ENDPOINTS['login'], {'email': 'intruso@x.co', 'password': 'nope'}, format='json')
    assert SecurityEvent.objects.filter(kind='login_failed', email='intruso@x.co').exists()


def test_crud_is_audited_with_field_changes(ctx):
    api = ctx['api']
    res = api.post(s.ENDPOINTS['customers'], {'first_name': 'Ana', 'email': 'ana@x.co'}, format='json')
    cid = res.data['id']
    api.patch(f"{s.ENDPOINTS['customers']}{cid}/", {'phone': '3001234567'}, format='json')
    api.delete(f"{s.ENDPOINTS['customers']}{cid}/")
    actions = [e.action for e in logs(ctx['t'], entity_type='customers.customer')]
    assert actions == ['customers.customer.created', 'customers.customer.updated', 'customers.customer.deleted']
    updated = logs(ctx['t'], action='customers.customer.updated')[0]
    assert updated.changes == {'phone': ['', '3001234567']}
    assert 'teléfono' in updated.summary


def test_price_change_emits_dedicated_event(ctx):
    product = s.make_product(ctx['t'], code='P-1', price='1800')
    ctx['api'].patch(f"{s.ENDPOINTS['products']}{product.id}/", {'price': '2000'}, format='json')
    event = logs(ctx['t'], action='catalog.product.price_changed')[0]
    assert event.changes == {'price': ['1800.00', '2000.00']}
    assert '1800.00 → 2000.00' in event.summary


def test_salary_changes_are_masked(ctx):
    employee = s.make_employee(ctx['t'])
    ctx['api'].patch(f"{s.ENDPOINTS['employees']}{employee.id}/", {'salary': '2500000'}, format='json')
    entry = logs(ctx['t'], action='hr.employee.updated')[0]
    assert entry.changes['salary'] == ['••••', '••••']
    assert '2500000' not in str(entry.changes)


def test_invoice_status_change_is_audited(ctx):
    customer, product = s.make_customer(ctx['t']), s.make_product(ctx['t'], code='P-2')
    res = ctx['api'].post(s.ENDPOINTS['invoices'], s.invoice_payload(customer.id, product.id), format='json')
    ctx['api'].patch(f"{s.ENDPOINTS['invoices']}{res.data['id']}/", {'status': 'paid'}, format='json')
    event = logs(ctx['t'], action='billing.invoice.status_changed')[0]
    assert event.changes == {'status': ['draft', 'paid']}


def test_audit_log_is_append_only_in_orm_and_database(ctx):
    entry = logs(ctx['t'])[0]
    with tenant_context(ctx['t']):
        entry.summary = 'manipulado'
        with pytest.raises(AppendOnlyError):
            entry.save()
        with pytest.raises(AppendOnlyError):
            entry.delete()
        with pytest.raises(AppendOnlyError):
            AuditLog.objects.update(summary='x')
    # El trigger de PostgreSQL bloquea incluso SQL directo
    with pytest.raises(Exception, match='solo inserción'), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("UPDATE audit_auditlog SET summary = 'x'")


def test_failed_operation_leaves_no_audit_entry(ctx):
    """El cambio y su auditoría son atómicos: si la operación falla, no queda registro."""
    customer, product = s.make_customer(ctx['t']), s.make_product(ctx['t'], code='P-3', is_active=False)
    before = len(logs(ctx['t']))
    res = ctx['api'].post(s.ENDPOINTS['invoices'], s.invoice_payload(customer.id, product.id), format='json')
    assert res.status_code == 400
    assert len(logs(ctx['t'])) == before


def test_audit_endpoint_requires_permission_and_filters(ctx):
    cashier = s.make_user(ctx['t'], 'caja@aud.co', 'CASHIER')
    assert s.api_for(cashier).get('/api/audit/').status_code == 403
    res = ctx['api'].get('/api/audit/', {'action': 'auth.'})
    assert res.status_code == 200
    assert res.data['count'] >= 1
    assert all(row['action'].startswith('auth.') for row in res.data['results'])


def test_invitation_acceptance_is_attributed_to_the_invited_person(ctx):
    from rest_framework.test import APIClient
    with tenant_context(ctx['t']):
        from gestorpro.core.access.models import Role
        role = Role.objects.get(code='CASHIER')
    url = ctx['api'].post('/api/access/invitations/', {'email': 'nueva@aud.co', 'role': role.id},
                          format='json').data['invite_url']
    APIClient().post('/api/auth/accept-invitation/', {'token': url.rsplit('/', 1)[1], 'password': 'Pan-de-yuca-2026',
                                                       'first_name': 'Nueva'}, format='json')
    entry = logs(ctx['t'], action='access.invitation.accepted')[0]
    assert entry.actor_label == 'nueva@aud.co'


def test_login_updates_last_login(ctx):
    ctx['admin'].refresh_from_db()
    assert ctx['admin'].last_login is not None
