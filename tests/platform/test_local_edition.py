"""Edición local: copias de seguridad, configuración segura y licencia sin vencimiento."""
import datetime
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import local_edition as le  # noqa: E402

D = datetime.datetime


# ── Copias de seguridad ─────────────────────────────────────────────────────

def test_backup_is_due_once_a_day_after_the_configured_hour():
    assert le.backup_due(None, D(2026, 10, 10, 8), 21)                        # nunca se hizo
    assert not le.backup_due(D(2026, 10, 9, 21, 5), D(2026, 10, 10, 8), 21)   # la de anoche sirve
    assert le.backup_due(D(2026, 10, 9, 21, 5), D(2026, 10, 10, 21, 1), 21)   # ya pasó la hora de hoy
    assert not le.backup_due(D(2026, 10, 10, 21, 2), D(2026, 10, 10, 23), 21)
    assert le.backup_due(D(2026, 10, 8, 20), D(2026, 10, 10, 8), 21)          # equipo apagado: más de 26 h


def test_rotation_keeps_the_newest_and_never_touches_other_files(tmp_path):
    for day in range(1, 8):
        (tmp_path / f'gestorpro-202610{day:02d}-210000.zip').write_bytes(b'x')
    (tmp_path / 'gestorpro-20261003-120000-antes-de-actualizar.zip').write_bytes(b'x')
    (tmp_path / 'fotos-de-la-panaderia.zip').write_bytes(b'x')
    (tmp_path / 'gestorpro-notas.txt').write_text('mías')
    removed = le.rotate(tmp_path, keep=3)
    kept = sorted(p.name for p in le.list_backups(tmp_path))
    assert kept == ['gestorpro-20261005-210000.zip', 'gestorpro-20261006-210000.zip', 'gestorpro-20261007-210000.zip']
    assert len(removed) == 5
    assert (tmp_path / 'fotos-de-la-panaderia.zip').exists() and (tmp_path / 'gestorpro-notas.txt').exists()


def test_backups_are_listed_newest_first_with_their_time(tmp_path):
    for name in ('gestorpro-20261001-210000.zip', 'gestorpro-20261009-073000-manual.zip',
                 'gestorpro-20261005-210000.zip'):
        (tmp_path / name).write_bytes(b'x')
    names = [p.name for p in le.list_backups(tmp_path)]
    assert names[0] == 'gestorpro-20261009-073000-manual.zip'
    assert le.backup_time(tmp_path / names[0]) == D(2026, 10, 9, 7, 30)
    assert le.backup_name(D(2026, 10, 9, 7, 30, 5), 'manual') == 'gestorpro-20261009-073005-manual.zip'


def test_restore_requires_the_exact_confirmation_word():
    assert le.confirmed('RESTAURAR') and le.confirmed('  RESTAURAR ')
    assert not any(le.confirmed(x) for x in ('', 's', 'si', 'restaurar', 'RESTAURAR YA'))


# ── Configuración ───────────────────────────────────────────────────────────

def test_generated_configuration_has_strong_secrets_and_no_demo_data(tmp_path):
    values = le.new_env_values()
    assert len(values['SECRET_KEY']) >= 64
    assert values['GESTORPRO_DB_PASSWORD'] != values['GESTORPRO_PG_SUPERUSER_PASSWORD']
    assert len(values['GESTORPRO_DB_PASSWORD']) >= 24
    assert le.new_env_values()['SECRET_KEY'] != values['SECRET_KEY']
    path = tmp_path / 'gestorpro.env'
    path.write_text(le.render_env(values), encoding='utf-8')
    assert le.read_env(path) == values
    le.write_env_value('GESTORPRO_COPIA_EXTRA', r'E:\Copias GestorPro', path)
    assert le.read_env(path)['GESTORPRO_COPIA_EXTRA'] == r'E:\Copias GestorPro'
    assert 'DEBUG' not in path.read_text() and 'Demo' not in path.read_text()


def test_allowed_hosts_cover_this_computer_and_the_local_network_only():
    hosts = le.allowed_hosts('CAJA-FAVORITA', ['192.168.1.40'])
    assert hosts == ['localhost', '127.0.0.1', 'caja-favorita', 'caja-favorita.local', '192.168.1.40']
    assert '*' not in hosts


def _settings(env_extra):
    code = ('import django, json; django.setup(); from django.conf import settings as s; '
            'print(json.dumps([s.DEBUG, s.SECURE_SSL_REDIRECT, s.SERVE_MEDIA, s.X_FRAME_OPTIONS, '
            's.SESSION_COOKIE_SECURE, str(s.MEDIA_ROOT)]))')
    env = {**os.environ, 'DJANGO_SETTINGS_MODULE': 'config.settings.local_edition',
           'DATABASE_URL': 'postgres://x@localhost/x', **env_extra}
    return subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env, capture_output=True, text=True)


def test_local_settings_are_production_grade_except_https():
    result = _settings({'SECRET_KEY': 'k' * 64, 'GESTORPRO_MEDIA_ROOT': '/datos/archivos'})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == '[false, false, true, "DENY", false, "/datos/archivos"]'


def test_local_settings_refuse_a_weak_secret_key():
    result = _settings({'SECRET_KEY': 'corta'})
    assert result.returncode != 0 and 'SECRET_KEY' in result.stderr


# ── Licencia ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_set_plan_no_end_makes_a_license_that_never_expires():
    from django.core.management import call_command

    from gestorpro.platform.subscriptions.models import Subscription
    from tests import support as s
    tenant = s.make_tenant('Licencia Local', plan_code='starter')
    sub = Subscription.objects.get(tenant=tenant)
    assert sub.status == Subscription.Status.TRIALING and sub.trial_ends_at is not None
    call_command('set_plan', tenant.slug, 'business', '--active', '--no-end')
    sub.refresh_from_db()
    assert (sub.plan.code, sub.status, sub.trial_ends_at, sub.current_period_end) == (
        'business', Subscription.Status.ACTIVE, None, None)
