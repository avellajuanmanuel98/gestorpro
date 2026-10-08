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
