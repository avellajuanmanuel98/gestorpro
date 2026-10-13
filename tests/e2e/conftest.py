"""
E2E en un navegador real (Chromium con Playwright) contra el backend servido
por el live_server de pytest-django y la SPA compilada (frontend/dist), igual
que en producción y en la edición local.

Se omiten si Playwright no está instalado o el frontend no está compilado,
salvo con E2E_REQUIRED=1 (CI), donde eso es un error.

    pip install -r requirements-e2e.txt && playwright install chromium
    pytest -m e2e
"""
import os
from pathlib import Path

import pytest
from django.conf import settings

REQUIRED = os.environ.get('E2E_REQUIRED') == '1'


def _unavailable(reason):
    if REQUIRED:
        pytest.fail(f'E2E obligatorio: {reason}')
    pytest.skip(reason)


@pytest.fixture
def browser(transactional_db):
    # Por test y DESPUÉS de preparar la base: como fixture de sesión se creaba antes y, tras otro
    # test transaccional, el test veía la base vacía (sin la restauración de serialized_rollback).
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _unavailable('Playwright no está instalado (requirements-e2e.txt)')
    if not (Path(settings.BASE_DIR) / 'frontend' / 'dist' / 'index.html').exists():
        _unavailable('frontend/dist no existe (npm run build)')
    # Django prohíbe consultas síncronas dentro de un event loop; Playwright crea uno en este hilo
    os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get('E2E_CHROMIUM_PATH') or None)
        yield b
        b.close()


@pytest.fixture
def new_page(browser, live_server):
    """Abre una pestaña nueva (sesión aparte) y falla el test si el navegador registra errores."""
    contexts, problems = [], []

    def make():
        ctx = browser.new_context(base_url=live_server.url, viewport={'width': 1366, 'height': 900},
                                  timezone_id='America/Bogota', locale='es-CO')
        ctx.set_default_timeout(15000)
        page = ctx.new_page()
        page.on('console', lambda m: problems.append(f'console: {m.text}') if m.type == 'error' else None)
        page.on('response', lambda r: problems.append(f'{r.status} {r.url}') if r.status >= 500 else None)
        contexts.append(ctx)
        return page

    yield make
    for ctx in contexts:
        ctx.close()
    assert problems == [], problems
