"""Despliegue en la nube (Render + Neon): configuración de producción y archivo render.yaml."""
import base64
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RANDOM_KEY = base64.b64encode(secrets.token_bytes(32)).decode()  # como la genera Render: 44 caracteres


def _prod(env_extra):
    code = ('import django, json; django.setup(); from django.conf import settings as s; '
            'print(json.dumps([s.ALLOWED_HOSTS, s.CSRF_TRUSTED_ORIGINS, s.FRONTEND_URL, s.SECURE_SSL_REDIRECT, '
            's.SECURE_REDIRECT_EXEMPT, s.DATABASES["default"]["CONN_HEALTH_CHECKS"]]))')
    env = {k: v for k, v in os.environ.items() if k not in ('RENDER_EXTERNAL_HOSTNAME', 'FRONTEND_URL')}
    env.update({'DJANGO_SETTINGS_MODULE': 'config.settings.prod', 'SECRET_KEY': RANDOM_KEY,
                'DATABASE_URL': 'postgres://u:p@ep-algo.us-east-2.aws.neon.tech/neondb?sslmode=require',
                **env_extra})
    return subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env, capture_output=True, text=True)


def test_render_domain_is_allowed_and_used_for_links():
    result = _prod({'RENDER_EXTERNAL_HOSTNAME': 'gestorpro-favorita.onrender.com'})
    assert result.returncode == 0, result.stderr
    hosts, origins, frontend, ssl_redirect, exempt, health_checks = json.loads(result.stdout)
    assert 'gestorpro-favorita.onrender.com' in hosts
    assert 'https://gestorpro-favorita.onrender.com' in origins
    assert frontend == 'https://gestorpro-favorita.onrender.com'
    assert ssl_redirect is True and exempt == [r'^api/health/$']
    assert health_checks is True  # Neon suspende la base: la conexión persistente se verifica antes de usarse


def test_an_explicit_frontend_url_wins_over_the_render_domain():
    result = _prod({'RENDER_EXTERNAL_HOSTNAME': 'x.onrender.com', 'FRONTEND_URL': 'https://app.lafavorita.co'})
    assert json.loads(result.stdout)[2] == 'https://app.lafavorita.co'


@pytest.mark.parametrize('key', ['corta', 'django-insecure-' + 'a' * 50, 'ab' * 30])
def test_weak_secret_keys_are_refused(key):
    result = _prod({'SECRET_KEY': key})
    assert result.returncode != 0 and 'SECRET_KEY' in result.stderr


@pytest.mark.parametrize('url', [
    'postgres://u:p@ep-algo-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require',
    'postgres://u:p@db.example.com:6543/app?pgbouncer=true',
])
def test_a_connection_pooler_is_refused_because_rls_lives_in_the_session(url):
    result = _prod({'DATABASE_URL': url})
    assert result.returncode != 0 and 'pooler' in result.stderr


def test_render_blueprint_is_free_and_builds_what_the_app_needs():
    text = (ROOT / 'render.yaml').read_text(encoding='utf-8')
    assert 'plan: free' in text and 'healthCheckPath: /api/health/' in text
    assert 'collectstatic' in text and 'migrate --noinput' in text  # migrate también instala RLS
    assert 'generateValue: true' in text and 'sync: false' in text  # SECRET_KEY generada; DATABASE_URL a mano
    assert 'seed_demo' not in text and 'flush' not in text and 'createsuperuser' not in text


@pytest.mark.django_db
def test_health_endpoint_needs_no_session_and_touches_no_data(client, django_assert_num_queries):
    with django_assert_num_queries(0):
        res = client.get('/api/health/')
    assert res.status_code == 200 and res.json() == {'ok': True}
    assert client.post('/api/health/').status_code == 405
