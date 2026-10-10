"""
GestorPro — EDICIÓN LOCAL: instalado en un computador del negocio y usado por la
red local (caja, tablet, celular del dueño). Lo usan los .bat de la carpeta local/.

    python scripts/local_edition.py instalar     # primera vez (se puede repetir)
    python scripts/local_edition.py iniciar      # arranca PostgreSQL y GestorPro; hace las copias diarias
    python scripts/local_edition.py copia        # copia de seguridad ahora
    python scripts/local_edition.py restaurar    # vuelve a una copia (conserva la base actual)
    python scripts/local_edition.py actualizar   # copia + trae la nueva versión + migra
    python scripts/local_edition.py estado       # cómo está todo

Todo vive en la carpeta de datos (por defecto %USERPROFILE%\\GestorPro-datos):

    gestorpro.env   configuración y secretos (generados al instalar; no compartir)
    db\\            base de datos PostgreSQL propia, solo accesible desde este equipo
    copias\\        copias de seguridad (.zip: base de datos + imágenes)
    archivos\\      imágenes subidas (productos, logo)
    registros\\     registros de GestorPro y de PostgreSQL

Reglas de seguridad (no negociables):
  - Nunca se borra ni se vacía una base de datos con datos. Restaurar crea una base
    nueva y la base anterior queda guardada con otro nombre.
  - No se cargan datos de demostración ni se crean superusuarios: el dueño define su
    contraseña con un enlace de invitación.
  - PostgreSQL escucha solo en este equipo y exige contraseña.
"""
import datetime
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parent.parent))  # para importar config.wsgi
from dev_local import EXE, IS_WINDOWS, ROOT, fail, find_pg_bin, port_in_use, say, step  # noqa: E402

HOME = Path(os.environ.get('GESTORPRO_HOME', Path.home() / 'GestorPro-datos'))
ENV_FILE = HOME / 'gestorpro.env'
DB_NAME = 'gestorpro'
APP_ROLE = 'gestorpro'
RESTORE_DB = 'gestorpro_restaurando'
KEEP_BACKUPS = 30
BACKUP_RE = re.compile(r'^gestorpro-(\d{8}-\d{6})(-[a-z-]+)?\.zip$')
SETTINGS = 'config.settings.local_edition'


# ── Configuración ───────────────────────────────────────────────────────────

def paths(home: Path = HOME) -> dict[str, Path]:
    return {'db': home / 'db', 'backups': home / 'copias', 'media': home / 'archivos', 'logs': home / 'registros'}


def render_env(values: dict) -> str:
    lines = ['# GestorPro — edición local. Contiene secretos: NO lo compartas ni lo subas a internet.',
             '# Puedes cambiar GESTORPRO_COPIA_EXTRA, GESTORPRO_HORA_COPIA y CASH_DIFFERENCE_TOLERANCE.']
    lines += [f'{k}={v}' for k, v in values.items()]
    return '\n'.join(lines) + '\n'


def new_env_values() -> dict:
    return {
        'SECRET_KEY': secrets.token_urlsafe(64),
        'GESTORPRO_DB_PASSWORD': secrets.token_urlsafe(24),
        'GESTORPRO_PG_SUPERUSER_PASSWORD': secrets.token_urlsafe(24),
        'GESTORPRO_PG_PORT': '5435',
        'GESTORPRO_HTTP_PORT': '8000',
        'GESTORPRO_COPIA_EXTRA': '',
        'GESTORPRO_HORA_COPIA': '21',
        'GESTORPRO_PLAN': 'business',
        'CASH_DIFFERENCE_TOLERANCE': '5000',
    }


def read_env(path: Path = ENV_FILE) -> dict:
    values = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, value = line.partition('=')
            values[key.strip()] = value.strip()
    return values


def write_env_value(key: str, value: str, path: Path = ENV_FILE):
    lines = path.read_text(encoding='utf-8').splitlines()
    out, found = [], False
    for line in lines:
        if line.split('=', 1)[0].strip() == key:
            out.append(f'{key}={value}')
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f'{key}={value}')
    path.write_text('\n'.join(out) + '\n', encoding='utf-8')


def require_installed() -> dict:
    if not ENV_FILE.exists():
        fail(f'GestorPro no está instalado en este equipo (no existe {ENV_FILE}).\n  Ejecuta primero 1-instalar.bat.')
    return read_env()


def lan_ips() -> list[str]:
    ips = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('10.255.255.255', 1))  # no envía nada: solo elige la interfaz de la red local
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        ips.update(info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET))
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith('127.') and not ip.startswith('169.254.'))


def allowed_hosts(hostname: str, ips: list[str]) -> list[str]:
    host = hostname.lower()
    hosts = ['localhost', '127.0.0.1', host, f'{host}.local', *ips]
    return list(dict.fromkeys(h for h in hosts if h))


def django_env(cfg: dict) -> dict:
    """Variables con las que corre Django en la edición local (se calculan en cada arranque)."""
    p = paths()
    port = cfg['GESTORPRO_HTTP_PORT']
    ips = lan_ips()
    hosts = allowed_hosts(socket.gethostname(), ips)
    origins = [f'http://{h}:{port}' for h in hosts]
    env = os.environ.copy()
    env.update({
        'DJANGO_SETTINGS_MODULE': SETTINGS,
        'PYTHONUTF8': '1',
        'SECRET_KEY': cfg['SECRET_KEY'],
        'DATABASE_URL': (f"postgres://{APP_ROLE}:{cfg['GESTORPRO_DB_PASSWORD']}@localhost:"
                         f"{cfg['GESTORPRO_PG_PORT']}/{DB_NAME}"),
        'ALLOWED_HOSTS': ','.join(hosts),
        'CSRF_TRUSTED_ORIGINS': ','.join(origins),
        'CORS_ALLOWED_ORIGINS': ','.join(origins),
        'FRONTEND_URL': f'http://{ips[0] if ips else "localhost"}:{port}',
        'DEFAULT_PLAN_CODE': cfg.get('GESTORPRO_PLAN', 'business'),
        'CASH_DIFFERENCE_TOLERANCE': cfg.get('CASH_DIFFERENCE_TOLERANCE', '5000'),
        'THROTTLE_AUTH': '20/min',
        'GROQ_API_KEY': cfg.get('GROQ_API_KEY', ''),
        'GESTORPRO_MEDIA_ROOT': str(p['media']),
        'GESTORPRO_LOG_FILE': str(p['logs'] / 'gestorpro.log'),
    })
    return env


def python() -> str:
    path = ROOT / 'venv' / ('Scripts' if IS_WINDOWS else 'bin') / f'python{EXE}'
    return str(path) if path.exists() else sys.executable


def manage(cfg: dict, *args, check=True, capture=False, extra_env: dict | None = None):
    env = django_env(cfg) | (extra_env or {})
    result = subprocess.run([python(), 'manage.py', *args], cwd=ROOT, env=env, text=True, check=False,
                            stdin=subprocess.DEVNULL, capture_output=capture, encoding='utf-8', errors='replace')
    if check and result.returncode != 0:
        if capture:
            say(result.stdout + result.stderr)
        fail(f'Falló: manage.py {" ".join(args)}')
    return result


# ── PostgreSQL ──────────────────────────────────────────────────────────────

class Postgres:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.bin = find_pg_bin()
        if self.bin is None:
            fail('No encontré PostgreSQL.\n'
                 '  Descarga los binarios (zip) de https://www.enterprisedb.com/download-postgresql-binaries,\n'
                 f'  descomprímelos en {Path.home() / "pgsql"} y vuelve a ejecutar.')
        self.data = paths()['db']
        self.port = cfg['GESTORPRO_PG_PORT']

    def tool(self, name: str) -> str:
        return str(self.bin / f'{name}{EXE}')

    def env(self, superuser=False) -> dict:
        env = os.environ.copy()
        env['PGPASSWORD'] = self.cfg['GESTORPRO_PG_SUPERUSER_PASSWORD' if superuser else 'GESTORPRO_DB_PASSWORD']
        return env

    def conn(self, superuser=False) -> list[str]:
        return ['-h', 'localhost', '-p', self.port, '-U', 'postgres' if superuser else APP_ROLE]

    def initialized(self) -> bool:
        return (self.data / 'PG_VERSION').exists()

    def init(self):
        if self.data.exists() and any(self.data.iterdir()):
            fail(f'La carpeta {self.data} no está vacía y no es una base de datos de GestorPro. Revísala a mano.')
        self.data.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', suffix='.txt') as f:
            f.write(self.cfg['GESTORPRO_PG_SUPERUSER_PASSWORD'])
            pwfile = f.name
        try:
            base = [self.tool('initdb'), '-D', str(self.data), '-U', 'postgres', f'--pwfile={pwfile}',
                    '-A', 'scram-sha-256', '-E', 'UTF8']
            # Orden alfabético en español (á, ñ) si PostgreSQL trae ICU; si no, orden binario
            ok = subprocess.run(base + ['--locale-provider=icu', '--icu-locale=es-CO', '--locale=C'],
                                capture_output=True, text=True, check=False).returncode == 0
            if not ok:
                say('  (PostgreSQL sin ICU: los nombres se ordenarán sin reglas del español.)')
                shutil.rmtree(self.data, ignore_errors=True)  # la creó el intento fallido (antes estaba vacía)
                result = subprocess.run(base + ['--no-locale'], capture_output=True, text=True, check=False)
                if result.returncode != 0:
                    fail('No se pudo crear la base de datos:\n' + result.stdout + result.stderr)
        finally:
            os.unlink(pwfile)

    def running(self) -> bool:
        return subprocess.run([self.tool('pg_ctl'), 'status', '-D', str(self.data)], capture_output=True,
                              check=False).returncode == 0

    def start(self):
        if self.running():
            return
        if port_in_use(int(self.port)):
            fail(f'El puerto {self.port} lo usa otro programa. Cambia GESTORPRO_PG_PORT en {ENV_FILE}.')
        log = paths()['logs'] / 'postgres.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        # Sin capturar la salida: en Windows el servidor hereda las tuberías y nunca volvería
        started = subprocess.run(
            [self.tool('pg_ctl'), 'start', '-D', str(self.data), '-l', str(log), '-w', '-t', '90',
             '-o', f'-p {self.port} -c listen_addresses=localhost'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if started.returncode != 0:
            tail = log.read_text(encoding='utf-8', errors='replace').splitlines()[-15:] if log.exists() else []
            fail('PostgreSQL no arrancó. Últimas líneas del registro:\n  ' + '\n  '.join(tail))

    def stop(self):
        if self.running():
            subprocess.run([self.tool('pg_ctl'), 'stop', '-D', str(self.data), '-m', 'fast', '-w'],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    def sql(self, statement: str, db: str = 'postgres') -> str:
        result = subprocess.run([self.tool('psql'), *self.conn(superuser=True), '-d', db, '-v', 'ON_ERROR_STOP=1',
                                 '-tAc', statement], env=self.env(superuser=True), capture_output=True, text=True,
                                check=False)
        if result.returncode != 0:
            fail(f'Error de PostgreSQL: {result.stderr.strip()}')
        return result.stdout.strip()

    def database_exists(self, name: str) -> bool:
        return self.sql(f"SELECT 1 FROM pg_database WHERE datname = '{name}'") == '1'

    def ensure_database(self):
        password = self.cfg['GESTORPRO_DB_PASSWORD'].replace("'", "''")
        if self.sql(f"SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}'") != '1':
            self.sql(f"CREATE ROLE {APP_ROLE} LOGIN PASSWORD '{password}'")
        if not self.database_exists(DB_NAME):
            self.sql(f'CREATE DATABASE {DB_NAME} OWNER {APP_ROLE}')

    def old_databases(self) -> list[tuple[str, str]]:
        rows = self.sql("SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database "
                        "WHERE datname LIKE 'gestorpro_antes_%' ORDER BY datname")
        return [tuple(r.split('|')) for r in rows.splitlines() if r]


# ── Copias de seguridad ─────────────────────────────────────────────────────

def backup_name(now: datetime.datetime, tag: str = '') -> str:
    return f"gestorpro-{now:%Y%m%d-%H%M%S}{f'-{tag}' if tag else ''}.zip"


def list_backups(folder: Path) -> list[Path]:
    """Copias de GestorPro en la carpeta, de la más nueva a la más vieja (ignora cualquier otro archivo)."""
    if not folder.is_dir():
        return []
    found = [p for p in folder.iterdir() if p.is_file() and BACKUP_RE.match(p.name)]
    return sorted(found, key=lambda p: BACKUP_RE.match(p.name).group(1), reverse=True)


def backup_time(path: Path) -> datetime.datetime:
    return datetime.datetime.strptime(BACKUP_RE.match(path.name).group(1), '%Y%m%d-%H%M%S')


def rotate(folder: Path, keep: int = KEEP_BACKUPS) -> list[Path]:
    """Deja las `keep` copias más recientes. Solo toca archivos con el nombre de las copias de GestorPro."""
    old = list_backups(folder)[keep:]
    for path in old:
        path.unlink()
    return old


def backup_due(last: datetime.datetime | None, now: datetime.datetime, hour: int) -> bool:
    """Toca copia si nunca se hizo, si ya pasó la hora del día y la de hoy no está, o si van más de 26 h."""
    if last is None:
        return True
    if now - last > datetime.timedelta(hours=26):
        return True
    mark = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    return now >= mark and last < mark


def make_backup(cfg: dict, tag: str = '', quiet: bool = False) -> Path:
    pg = Postgres(cfg)
    p = paths()
    p['backups'].mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now()
    target = p['backups'] / backup_name(now, tag)
    with tempfile.TemporaryDirectory() as tmp:
        dump = Path(tmp) / 'base.dump'
        result = subprocess.run([pg.tool('pg_dump'), *pg.conn(), '-d', DB_NAME, '-Fc', '-f', str(dump)],
                                env=pg.env(), capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f'pg_dump falló: {result.stderr.strip()}')
        # Verificación: una copia que no se puede leer no es una copia
        check = subprocess.run([pg.tool('pg_restore'), '--list', str(dump)], capture_output=True, check=False)
        if check.returncode != 0 or dump.stat().st_size == 0:
            raise RuntimeError('La copia generada no se pudo verificar.')
        partial = target.with_suffix('.partial')
        with zipfile.ZipFile(partial, 'w', zipfile.ZIP_DEFLATED) as z:
            z.write(dump, 'base.dump')
            z.writestr('copia.json', json.dumps({'creada': now.isoformat(timespec='seconds'), 'version': version()}))
            if p['media'].is_dir():
                for f in p['media'].rglob('*'):
                    if f.is_file():
                        z.write(f, Path('archivos') / f.relative_to(p['media']))
        partial.replace(target)
    rotate(p['backups'])
    extra = cfg.get('GESTORPRO_COPIA_EXTRA', '').strip()
    if extra:
        try:
            Path(extra).mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, Path(extra) / target.name)
            rotate(Path(extra))
        except OSError as exc:
            log_line(f'No se pudo copiar a la carpeta extra {extra}: {exc}')
            if not quiet:
                say(f'  [AVISO] No se pudo copiar a la carpeta extra ({extra}): {exc}')
    log_line(f'Copia creada: {target.name} ({target.stat().st_size // 1024} KB)')
    return target


def log_line(text: str):
    log = paths()['logs'] / 'copias.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('a', encoding='utf-8') as f:
        f.write(f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {text}\n')


def last_backup(cfg: dict) -> datetime.datetime | None:
    backups = list_backups(paths()['backups'])
    return backup_time(backups[0]) if backups else None


def backup_loop(cfg: dict, stop: threading.Event):
    """Copias automáticas mientras GestorPro está abierto (no requiere permisos de administrador)."""
    hour = int(cfg.get('GESTORPRO_HORA_COPIA', '21') or 21)
    while not stop.is_set():
        try:
            if backup_due(last_backup(cfg), datetime.datetime.now(), hour):
                path = make_backup(cfg, quiet=True)
                say(f'  Copia de seguridad automática: {path.name}')
        except Exception as exc:  # noqa: BLE001 — una copia fallida no debe tumbar el servidor
            log_line(f'ERROR en la copia automática: {exc}')
            say(f'  [AVISO] Falló la copia automática: {exc} (se reintenta en 10 minutos)')
        stop.wait(600)


def version() -> str:
    git = shutil.which('git')
    if not git:
        return 'desconocida'
    result = subprocess.run([git, 'log', '-1', '--format=%h %cd', '--date=short'], cwd=ROOT, capture_output=True,
                            text=True, check=False)
    return result.stdout.strip() or 'desconocida'


# ── Comandos ────────────────────────────────────────────────────────────────

def ask(prompt: str, default: str = '') -> str:
    answer = input(f'  {prompt}{f" [{default}]" if default else ""}: ').strip()
    return answer or default


def install():
    step('1/7  Carpeta de datos')
    for key, folder in paths().items():
        if key != 'db':  # la crea initdb
            folder.mkdir(parents=True, exist_ok=True)
    if ENV_FILE.exists():
        say(f'  Ya existe {ENV_FILE}: se conserva (no se cambian contraseñas).')
    else:
        ENV_FILE.write_text(render_env(new_env_values()), encoding='utf-8')
        say(f'  Configuración creada en {ENV_FILE}')
    cfg = read_env()

    step('2/7  Base de datos')
    pg = Postgres(cfg)
    say(f'  PostgreSQL: {pg.bin}')
    if not pg.initialized():
        say(f'  Creando la base de datos en {pg.data} ...')
        pg.init()
    pg.start()
    pg.ensure_database()
    say('  Base de datos lista (solo accesible desde este equipo, con contraseña).')

    step('3/7  Estructura de la base de datos')
    manage(cfg, 'migrate', '--noinput', capture=True)
    say('  Lista.')
    step('4/7  Archivos de la aplicación')
    manage(cfg, 'collectstatic', '--noinput', capture=True)
    if not (ROOT / 'frontend' / 'dist' / 'index.html').exists():
        fail('Falta la aplicación compilada (frontend/dist). Descarga de nuevo el código.')
    say('  Listo.')

    step('5/7  Empresa')
    has_tenant = manage(cfg, 'shell', '--no-imports', '-c', 'from gestorpro.core.tenancy.models import Tenant;'
                        'print(Tenant.objects.exists())', capture=True).stdout.strip().endswith('True')
    if has_tenant:
        say('  La empresa ya existe: no se crea otra.')
    else:
        name = ask('Nombre del negocio', 'Panadería La Favorita')
        email = ''
        while '@' not in email:
            email = ask('Email del dueño (con él entrará al sistema)')
        bakery = ask('¿Es una panadería? (S/n)', 'S').lower() != 'n'
        city = ask('Ciudad', 'Bogotá')
        plan = cfg.get('GESTORPRO_PLAN', 'business')
        vertical = 'bakery' if bakery else 'generic'
        local_url = {'FRONTEND_URL': f"http://localhost:{cfg['GESTORPRO_HTTP_PORT']}"}
        result = manage(cfg, 'onboard_tenant', name, email, '--vertical', vertical, '--plan', plan, '--city', city,
                        capture=True, extra_env=local_url)
        say(result.stdout)
        slug = manage(cfg, 'shell', '--no-imports', '-c', 'from gestorpro.core.tenancy.models import Tenant;'
                      'print(Tenant.objects.order_by("id").first().slug)', capture=True).stdout.strip().splitlines()[-1]
        manage(cfg, 'set_plan', slug, plan, '--active', '--no-end', capture=True)  # licencia sin vencimiento
        if bakery:
            manage(cfg, 'load_starter_catalog', slug, capture=True)
            say('  Se cargaron los ingredientes comunes de panadería (sin precios ni existencias).')
        (HOME / 'LEEME-invitacion.txt').write_text(
            'Abre este enlace en el computador de GestorPro (con GestorPro iniciado) para definir la contraseña\n'
            'del dueño. Vence en 7 días. Si se pierde, se regenera con:\n'
            f'  python manage.py onboard_tenant --reinvite {slug} {email}\n\n' + result.stdout, encoding='utf-8')
        say(f'  (El enlace también quedó guardado en {HOME / "LEEME-invitacion.txt"})')

    step('6/7  Copias de seguridad')
    if not cfg.get('GESTORPRO_COPIA_EXTRA'):
        say('  Las copias se guardan en este equipo. Si el disco se daña, se pierden con él.')
        say('  Recomendado: una segunda carpeta en otra unidad (USB, disco externo) o sincronizada')
        say('  con la nube (OneDrive, Google Drive).')
        extra = ask('Carpeta para la segunda copia (Enter para omitir por ahora)')
        if extra:
            write_env_value('GESTORPRO_COPIA_EXTRA', extra)
            cfg = read_env()
    path = make_backup(cfg, tag='instalacion')
    say(f'  Primera copia creada: {path}')

    step('7/7  Arranque automático')
    if IS_WINDOWS:
        if ask('¿Abrir GestorPro automáticamente al encender el computador? (S/n)', 'S').lower() != 'n':
            install_autostart()
        try_firewall(cfg['GESTORPRO_HTTP_PORT'])
    else:
        say('  (Solo en Windows.)')

    say('\nInstalación lista. Abre GestorPro con "GestorPro.bat" (o reinicia el computador si activaste el')
    say('arranque automático) y luego abre el enlace de invitación para crear la contraseña del dueño.')


def startup_folder() -> Path:
    return Path(os.environ.get('APPDATA', '')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup'


def install_autostart():
    folder = startup_folder()
    if not folder.is_dir():
        say('  No encontré la carpeta de Inicio de Windows: omitido.')
        return
    launcher = folder / 'GestorPro.cmd'
    target = ROOT / 'local' / 'GestorPro.bat'
    launcher.write_text(f'@echo off\r\nstart "GestorPro" /min "{target}"\r\n', encoding='utf-8')
    say(f'  Listo: GestorPro se abrirá minimizado al iniciar sesión ({launcher}).')


def try_firewall(port: str):
    result = subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule', 'name=GestorPro', 'dir=in',
                             'action=allow', 'protocol=TCP', f'localport={port}', 'profile=private'],
                            capture_output=True, text=True, check=False)
    if result.returncode == 0:
        say(f'  Firewall: permitido el puerto {port} en redes privadas (tablet y celulares de la red local).')
    else:
        say('  Firewall: la primera vez que inicies GestorPro, Windows preguntará si permites el acceso.')
        say('  Marca "Redes privadas" y acepta, para poder entrar desde la tablet o el celular.')


def serve():
    cfg = require_installed()
    port = int(cfg['GESTORPRO_HTTP_PORT'])
    if port_in_use(port):
        fail(f'GestorPro ya está abierto (o el puerto {port} lo usa otro programa).\n'
             f'  Ábrelo en el navegador: http://localhost:{port}')
    step('Base de datos')
    pg = Postgres(cfg)
    pg.start()
    say('  En marcha.')
    env = django_env(cfg)
    os.environ.update(env)
    step('Actualizando estructura (si hace falta)')
    manage(cfg, 'migrate', '--noinput', capture=True)

    stop = threading.Event()
    threading.Thread(target=backup_loop, args=(cfg, stop), daemon=True).start()

    from waitress import serve as waitress_serve

    from config.wsgi import application

    forget_used_invitation()
    ips = lan_ips()
    say('\n' + '=' * 64)
    say('  GestorPro está abierto. NO cierres esta ventana (puedes minimizarla).')
    say(f'  En este computador:     http://localhost:{port}')
    for ip in ips:
        say(f'  Desde tablet o celular: http://{ip}:{port}   (misma red wifi)')
    say(f'  Copias de seguridad:    {paths()["backups"]}  (cada día a las {cfg.get("GESTORPRO_HORA_COPIA", "21")}:00)')
    say('=' * 64 + '\n')
    if IS_WINDOWS:
        import webbrowser
        threading.Timer(2.0, lambda: webbrowser.open(f'http://localhost:{port}')).start()
    def _stop(*_):
        raise KeyboardInterrupt
    for name in ('SIGTERM', 'SIGBREAK'):  # SIGBREAK: Ctrl+Pausa o cerrar la ventana en Windows
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _stop)
    try:
        waitress_serve(application, listen=f'0.0.0.0:{port}', threads=8, ident='GestorPro')
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        say('Cerrando la base de datos ...')
        pg.stop()


def forget_used_invitation():
    """El enlace guardado al instalar se borra en cuanto ya no hay invitaciones pendientes."""
    note = HOME / 'LEEME-invitacion.txt'
    if not note.exists():
        return
    from django.utils import timezone

    from gestorpro.core.access.models import Invitation
    pending = Invitation.all_tenants.filter(accepted_at__isnull=True, revoked_at__isnull=True,
                                            expires_at__gt=timezone.now()).exists()
    if not pending:
        note.unlink()


def backup_now():
    cfg = require_installed()
    Postgres(cfg).start()
    step('Copia de seguridad')
    try:
        path = make_backup(cfg, tag='manual')
    except RuntimeError as exc:
        fail(str(exc))
    say(f'  Lista: {path}  ({path.stat().st_size // 1024} KB)')
    if cfg.get('GESTORPRO_COPIA_EXTRA'):
        say(f'  También en: {cfg["GESTORPRO_COPIA_EXTRA"]}')


def require_closed(cfg: dict):
    if port_in_use(int(cfg['GESTORPRO_HTTP_PORT'])):
        fail('GestorPro está abierto. Ciérralo primero (cierra la ventana de GestorPro) y vuelve a intentar.')


def restore():
    cfg = require_installed()
    require_closed(cfg)
    pg = Postgres(cfg)
    pg.start()
    candidates = list_backups(paths()['backups'])
    extra = cfg.get('GESTORPRO_COPIA_EXTRA', '').strip()
    if extra:
        names = {p.name for p in candidates}
        candidates += [p for p in list_backups(Path(extra)) if p.name not in names]
        candidates.sort(key=lambda p: BACKUP_RE.match(p.name).group(1), reverse=True)
    if not candidates:
        fail('No hay copias de seguridad para restaurar.')
    step('Copias disponibles')
    for i, path in enumerate(candidates[:20], 1):
        say(f'  {i:>2}. {backup_time(path):%Y-%m-%d %H:%M}  {path.stat().st_size // 1024:>7} KB  {path.parent}')
    choice = ask('Número de la copia a restaurar (Enter para cancelar)')
    if not choice.isdigit() or not 1 <= int(choice) <= min(20, len(candidates)):
        fail('Cancelado. No se cambió nada.')
    source = candidates[int(choice) - 1]
    say(f'\n  Vas a volver a como estaba todo el {backup_time(source):%Y-%m-%d a las %H:%M}.')
    say('  Lo registrado después de esa hora NO aparecerá (la base actual se guarda aparte, no se borra).')
    if not confirmed(ask('Escribe RESTAURAR para continuar')):
        fail('Cancelado. No se cambió nada.')

    step('1/4  Copia de seguridad de cómo está ahora')
    say(f'  {make_backup(cfg, tag="antes-de-restaurar").name}')
    step('2/4  Leyendo la copia')
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(source) as z:
            z.extractall(tmp)
        dump = Path(tmp) / 'base.dump'
        if not dump.exists():
            fail('La copia no contiene la base de datos.')
        if pg.database_exists(RESTORE_DB):
            pg.sql(f'DROP DATABASE {RESTORE_DB}')  # solo la base temporal de un intento anterior fallido
        pg.sql(f'CREATE DATABASE {RESTORE_DB} OWNER {APP_ROLE}')
        result = subprocess.run([pg.tool('pg_restore'), *pg.conn(superuser=True), '-d', RESTORE_DB, '--no-owner',
                                 f'--role={APP_ROLE}', '--exit-on-error', str(dump)],
                                env=pg.env(superuser=True), capture_output=True, text=True, check=False)
        if result.returncode != 0:
            fail(f'No se pudo leer la copia (la base actual no se tocó):\n{result.stderr.strip()}')
        step('3/4  Cambiando a la base restaurada')
        keep = f'gestorpro_antes_{datetime.datetime.now():%Y%m%d_%H%M%S}'
        pg.sql(f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{DB_NAME}'")
        pg.sql(f'ALTER DATABASE {DB_NAME} RENAME TO {keep}')
        pg.sql(f'ALTER DATABASE {RESTORE_DB} RENAME TO {DB_NAME}')
        media_src = Path(tmp) / 'archivos'
        if media_src.is_dir():
            media = paths()['media']
            if media.exists():
                media.rename(media.with_name(f'archivos_antes_{datetime.datetime.now():%Y%m%d_%H%M%S}'))
            shutil.copytree(media_src, media)
    step('4/4  Ajustando la estructura a esta versión')
    manage(cfg, 'migrate', '--noinput', capture=True)
    say(f'\nListo. La base anterior quedó guardada como "{keep}" (no se borró).')
    say('Abre GestorPro de nuevo con GestorPro.bat.')


def confirmed(text: str) -> bool:
    return text.strip() == 'RESTAURAR'


def update():
    cfg = require_installed()
    require_closed(cfg)
    git = shutil.which('git')
    if not git:
        fail('No encontré Git: instálalo (git-scm.com) para poder actualizar.')
    dirty = subprocess.run([git, 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT, capture_output=True,
                           text=True, check=False).stdout.strip()
    if dirty:
        fail('Hay archivos del programa modificados en este equipo; no se actualiza para no perderlos:\n' + dirty)
    Postgres(cfg).start()
    before = version()
    step('1/4  Copia de seguridad antes de actualizar')
    say(f'  {make_backup(cfg, tag="antes-de-actualizar").name}')
    step('2/4  Descargando la nueva versión')
    branch = subprocess.run([git, 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=ROOT, capture_output=True, text=True,
                            check=False).stdout.strip()
    if subprocess.run([git, 'pull', '--ff-only', 'origin', branch], cwd=ROOT, check=False).returncode != 0:
        fail('No se pudo descargar la actualización (¿sin internet?). No se cambió nada.')
    step('3/4  Dependencias')
    if subprocess.run([python(), '-m', 'pip', 'install', '--disable-pip-version-check', '-q', '-r',
                       'requirements.txt'], cwd=ROOT, check=False).returncode != 0:
        fail('Falló la instalación de dependencias. GestorPro sigue con la base intacta; revisa la conexión.')
    step('4/4  Estructura de la base de datos y archivos')
    manage(cfg, 'migrate', '--noinput')
    manage(cfg, 'collectstatic', '--noinput', capture=True)
    say(f'\nActualizado: {before}  →  {version()}')
    say('Abre GestorPro de nuevo con GestorPro.bat.')


def status():
    cfg = require_installed()
    port = cfg['GESTORPRO_HTTP_PORT']
    step('GestorPro')
    say(f'  Versión: {version()}')
    say(f'  Abierto: {"sí" if port_in_use(int(port)) else "no"}')
    say(f'  En este computador: http://localhost:{port}')
    for ip in lan_ips():
        say(f'  Desde la red local: http://{ip}:{port}')
    step('Copias de seguridad')
    backups = list_backups(paths()['backups'])
    if not backups:
        say('  [AVISO] Aún no hay copias.')
    else:
        age = datetime.datetime.now() - backup_time(backups[0])
        hours = age.total_seconds() / 3600
        say(f'  Última: {backup_time(backups[0]):%Y-%m-%d %H:%M} (hace {hours:.0f} h) · {len(backups)} guardadas')
        if hours > 48:
            say('  [AVISO] La última copia tiene más de 2 días. ¿GestorPro ha estado cerrado? Haz una copia ahora.')
    extra = cfg.get('GESTORPRO_COPIA_EXTRA', '').strip()
    if not extra:
        say('  [AVISO] Sin segunda copia fuera de este disco. Define GESTORPRO_COPIA_EXTRA en ' + str(ENV_FILE))
    elif not Path(extra).is_dir():
        say(f'  [AVISO] La carpeta de la segunda copia no está disponible ahora: {extra}')
    else:
        say(f'  Segunda copia: {extra} ({len(list_backups(Path(extra)))} guardadas)')
    free = shutil.disk_usage(HOME).free / 1024 ** 3
    say(f'  Espacio libre en disco: {free:.1f} GB' + ('  [AVISO] poco espacio' if free < 2 else ''))
    pg = Postgres(cfg)
    if pg.running():
        old = pg.old_databases()
        if old:
            step('Bases anteriores guardadas al restaurar (no se borran solas)')
            for name, size in old:
                say(f'  {name}  ({size})')


COMMANDS = {'instalar': install, 'iniciar': serve, 'copia': backup_now, 'restaurar': restore,
            'actualizar': update, 'estado': status}

if __name__ == '__main__':
    os.environ.setdefault('PYTHONUTF8', '1')
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        fail('Uso: python scripts/local_edition.py ' + '|'.join(COMMANDS))
    COMMANDS[sys.argv[1]]()
