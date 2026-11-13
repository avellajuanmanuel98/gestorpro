"""Fase 12: cabeceras de seguridad, también en la página que sirve WhiteNoise (index.html)."""
import pytest
from django.test import Client

pytestmark = [pytest.mark.isolation, pytest.mark.django_db]

CSP_MUST = ["default-src 'self'", "script-src 'self'", "object-src 'none'", "frame-ancestors 'none'",
            "base-uri 'self'", "form-action 'self'"]


def _csp(res):
    return res.headers.get('Content-Security-Policy', '')


def test_the_app_page_forbids_inline_scripts_framing_and_foreign_origins():
    res = Client().get('/')
    assert res.status_code == 200
    policy = _csp(res)
    for directive in CSP_MUST:
        assert directive in policy
    assert 'unsafe-inline' not in policy and 'unsafe-eval' not in policy
    assert res.headers['X-Frame-Options'] == 'DENY'
    assert res.headers['X-Content-Type-Options'] == 'nosniff'
    assert 'camera=()' in res.headers['Permissions-Policy']


def test_deep_links_of_the_app_have_the_same_policy():
    res = Client().get('/inventory/movements')
    assert res.status_code == 200 and "script-src 'self'" in _csp(res)


def test_api_responses_carry_the_policy_too():
    res = Client().post('/api/auth/login/', {'email': 'x@x.co', 'password': 'x'}, content_type='application/json')
    assert "default-src 'self'" in _csp(res) and res.headers['X-Content-Type-Options'] == 'nosniff'
    assert res.headers['Cache-Control'] == 'no-store'  # datos del negocio: ni navegador ni proxy los guardan


def test_api_docs_are_not_published_outside_development():
    assert Client().get('/api/docs/').status_code == 404
    assert Client().get('/api/schema/').status_code == 404
