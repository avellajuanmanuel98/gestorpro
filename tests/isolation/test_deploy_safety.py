"""S3/S4: ningún despliegue puede destruir la BD ni crear superusuarios públicos."""
import pathlib

import pytest

pytestmark = [pytest.mark.isolation]

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_no_destructive_command_in_deploy():
    procfile = (ROOT / 'Procfile').read_text()
    assert 'wipe_db' not in procfile
    assert 'flush' not in procfile
    assert not list(ROOT.glob('**/management/commands/wipe_db.py'))


def test_deploy_does_not_seed_demo_data():
    assert 'seed' not in (ROOT / 'Procfile').read_text()


def test_no_public_demo_credentials_in_repo():
    for path in [ROOT / 'README.md', *ROOT.glob('**/management/commands/*.py')]:
        if 'node_modules' in path.parts:
            continue
        assert 'demo1234' not in path.read_text(), path


@pytest.mark.django_db
def test_demo_seed_never_creates_superuser():
    from django.contrib.auth import get_user_model
    from django.core.management import call_command, get_commands
    commands = [c for c in ('seed_demo',) if c in get_commands()]
    for c in commands:
        try:
            call_command(c)
        except Exception:
            pass
    assert not get_user_model().objects.filter(is_superuser=True).exists()


@pytest.mark.django_db
def test_demo_seed_refuses_to_run_in_production_settings():
    from django.core.management import call_command
    from django.core.management.base import CommandError
    with pytest.raises(CommandError):
        call_command('seed_demo')


@pytest.mark.django_db
def test_demo_seed_in_debug_creates_bakery_without_superuser(settings):
    from django.contrib.auth import get_user_model
    from django.core.management import call_command
    settings.DEBUG = True
    call_command('seed_demo')
    call_command('seed_demo')  # idempotente
    User = get_user_model()
    assert User.objects.filter(email='propietaria@demo.miga.co').count() == 1
    assert not User.objects.filter(is_superuser=True).exists()
    assert not User.objects.filter(is_staff=True).exists()


def test_local_edition_never_seeds_demo_data_nor_destroys_databases():
    script = (ROOT / 'scripts' / 'local_edition.py').read_text(encoding='utf-8')
    launchers = ''.join(p.read_text(encoding='utf-8') for p in (ROOT / 'local').glob('*.bat'))
    for text in (script, launchers):
        assert 'seed_demo' not in text and 'flush' not in text and 'wipe' not in text
        assert 'createsuperuser' not in text and 'dropdb' not in text
    # El único DROP permitido es el de la base TEMPORAL de una restauración fallida
    drops = [line.strip() for line in script.splitlines() if 'DROP DATABASE' in line]
    assert drops == ["pg.sql(f'DROP DATABASE {RESTORE_DB}')  # solo la base temporal de un intento anterior fallido"]
    assert "RESTORE_DB = 'gestorpro_restaurando'" in script


def test_local_edition_runs_with_debug_off():
    settings_file = (ROOT / 'config' / 'settings' / 'local_edition.py').read_text(encoding='utf-8')
    assert 'DEBUG = False' in settings_file and 'DEBUG = True' not in settings_file


def test_committed_frontend_build_is_complete():
    """index.html no puede apuntar a archivos que no estén en el repositorio (la edición local no compila)."""
    import re
    dist = ROOT / 'frontend' / 'dist'
    assets = re.findall(r'(?:src|href)="/(assets/[^"]+)"', (dist / 'index.html').read_text(encoding='utf-8'))
    assert any(a.endswith('.js') for a in assets)
    missing = [a for a in assets if not (dist / a).exists()]
    assert not missing, missing
