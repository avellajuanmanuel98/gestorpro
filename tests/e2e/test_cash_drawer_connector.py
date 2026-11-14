"""
Al cobrar con "solo abrir cajón": si el Conector de Miga corre en el equipo (conector/MigaConector.ps1),
el cajón se abre por él y NO se imprime nada; si no está, se imprime la línea mínima de respaldo.
Un servidor local con el mismo protocolo hace de conector. Cubre también la CSP (connect-src).
"""
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from tests.e2e.test_sale_to_report import bakery, login  # noqa: F401  (fixture compartida)

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True, serialized_rollback=True)]
DISPLAY = {'state': {'textSize': 'normal', 'easyMode': False, 'saleAction': 'drawer', 'coinSound': False},
           'version': 1}
SEED_DISPLAY = ("if (!localStorage.getItem('gestorpro-display')) "
                f"localStorage.setItem('gestorpro-display', {json.dumps(json.dumps(DISPLAY))})")
# Como Chrome con --kiosk-printing: print() vuelve sin imprimir aún; se cuenta cuántas veces se pidió
COUNT_PRINTS = 'window.__prints = 0; window.print = () => { window.__prints++ }'
HITS = []  # pedidos que recibió el conector de prueba


class FakeConnector(BaseHTTPRequestHandler):
    """Mismo protocolo que conector/MigaConector.ps1."""

    def _send(self, status, body=b''):
        self.send_response(status)
        origin = self.headers.get('Origin')
        if origin:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        HITS.append(('OPTIONS', self.path))
        self._send(204)

    def do_GET(self):
        HITS.append(('GET', self.path))
        self._send(200, b'{"ok":true,"app":"miga-conector"}')

    def do_POST(self):
        HITS.append(('POST', self.path))
        self._send(200, b'{"ok":true}')

    def log_message(self, *args):
        pass


def sell(page):
    for _ in range(3):
        page.get_by_role('button', name=re.compile('Pan de bono')).first.click()
    page.get_by_role('button', name=re.compile('^Cobrar')).click()
    page.get_by_role('dialog', name='Cobrar').get_by_role('button', name='Confirmar pago').click()
    page.get_by_role('dialog', name='Venta registrada').wait_for()
    page.wait_for_timeout(2200)  # el conector tiene 1,5 s para responder antes del respaldo


def test_drawer_opens_through_the_connector_without_printing(bakery, browser, live_server):  # noqa: F811
    # Contexto propio: el caso "sin conector" registra ERR_CONNECTION_REFUSED en consola a propósito
    page = browser.new_context(base_url=live_server.url).new_page()
    page.set_default_timeout(15000)
    page.add_init_script(COUNT_PRINTS)
    page.add_init_script(SEED_DISPLAY)
    login(page, 'cajero@e2e.co')
    page.wait_for_url('**/pos')
    page.get_by_label('Base inicial en efectivo').fill('100000')
    page.get_by_role('button', name='Abrir caja').click()

    # 1) Sin conector: respaldo, se imprime la línea mínima
    sell(page)
    assert page.evaluate('window.__prints') == 1
    page.evaluate("window.dispatchEvent(new Event('afterprint'))")
    page.get_by_role('button', name='Nueva venta').click()
    page.get_by_role('button', name='Pantalla e impresora').click()
    page.get_by_text('Conector del cajón: no instalado').wait_for()
    page.get_by_role('button', name='Pantalla e impresora').click()

    # 2) Con conector: el cajón se abre por él y NO se imprime nada
    server = ThreadingHTTPServer(('127.0.0.1', 17777), FakeConnector)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        sell(page)
        assert ('POST', '/cajon') in HITS, HITS
        assert page.evaluate('window.__prints') == 1
        page.get_by_role('button', name='Nueva venta').click()
        page.get_by_role('button', name='Pantalla e impresora').click()
        page.get_by_text('Conector del cajón: funcionando').wait_for()

        # El botón "Abrir cajón" también va por el conector, sin papel
        HITS.clear()
        page.get_by_role('button', name='Abrir cajón', exact=True).click()
        page.wait_for_timeout(800)
        assert ('POST', '/cajon') in HITS and page.evaluate('window.__prints') == 1
    finally:
        server.shutdown()
        server.server_close()
