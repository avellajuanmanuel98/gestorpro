"""
Entorno local de desarrollo en Windows (lo usan instalar.bat e iniciar.bat).

    python scripts/dev_local.py setup   # primera vez o tras actualizar: deja todo listo
    python scripts/dev_local.py start   # arranca base de datos, backend y frontend

Qué hace `setup` (es seguro repetirlo):
  1. Trae los últimos cambios de la rama actual (git pull), si no hay cambios locales.
  2. Busca PostgreSQL y Node.js (en el PATH o en las carpetas habituales).
  3. Si no existe `.env`, lo crea con una base de datos PROPIA de este script:
     un clúster de PostgreSQL en %USERPROFILE%\\gestorpro-db, puerto 5434, solo
     accesible desde este equipo. Si ya tienes un `.env`, se respeta tal cual.
  4. Instala dependencias del frontend, aplica migraciones y crea los datos demo.
  5. Opcional: da de alta "Panadería La Favorita" con su catálogo base.

Solo para DESARROLLO. Nada de esto se usa en producción.
"""
import glob
import hashlib
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / 'frontend'
ENV_FILE = ROOT / '.env'
MANAGED_MARK = '# gestionado por scripts/dev_local.py'
PG_DATA = Path(os.environ.get('GESTORPRO_PG_DATA', Path.home() / 'gestorpro-db'))
PG_PORT = int(os.environ.get('GESTORPRO_PG_PORT', '5434'))
DB_NAME = 'gestorpro'
IS_WINDOWS = os.name == 'nt'
EXE = '.exe' if IS_WINDOWS else ''


def say(text=''):
    print(text, flush=True)


def step(text):
    say(f'\n==> {text}')


def fail(text):
    say(f'\n[ERROR] {text}')
    sys.exit(1)


def run(cmd, cwd=ROOT, check=True, capture=False, env=None):
    result = subprocess.run(cmd, cwd=cwd, check=False, text=True, env=env,
                            capture_output=capture, encoding='utf-8', errors='replace')
    if check and result.returncode != 0:
        if capture:
            say(result.stdout + result.stderr)
        fail(f'Falló el comando: {" ".join(map(str, cmd))}')
    return result


def venv_python():
    path = ROOT / 'venv' / ('Scripts' if IS_WINDOWS else 'bin') / f'python{EXE}'
    if not path.exists():
        fail('No existe el entorno virtual. Ejecuta primero instalar.bat.')
    return str(path)


def manage(*args, capture=False, check=True):
    return run([venv_python(), 'manage.py', *args], capture=capture, check=check)


# ── Herramientas ────────────────────────────────────────────────────────────

def find_pg_bin() -> Path | None:
    candidates = []
    if os.environ.get('PG_BIN'):
        candidates.append(Path(os.environ['PG_BIN']))
    if shutil.which('pg_ctl'):
        candidates.append(Path(shutil.which('pg_ctl')).parent)
    home = Path.home()
    patterns = [r'C:\Program Files\PostgreSQL\*\bin', str(home / 'pgsql' / 'bin'), str(home / '*' / 'pgsql' / 'bin'),
                str(home / 'Downloads' / '*' / 'pgsql' / 'bin'), str(home / 'Downloads' / 'pgsql' / 'bin'),
                r'C:\pgsql\bin']
    for pattern in patterns:
        candidates += [Path(p) for p in sorted(glob.glob(pattern), reverse=True)]
    return next((c for c in candidates if (c / f'pg_ctl{EXE}').exists()), None)


def find_npm() -> str | None:
    found = shutil.which('npm')
    if found:
        return found
    home = Path.home()
    # El zip de Node a veces queda en una carpeta doble (node-v24…\node-v24…\npm.cmd)
    bases = [home, home / 'Downloads']
    patterns = [str(b / sub / 'npm.cmd') for sub in ('node-v*', Path('node-v*') / 'node-v*') for b in bases]
    for pattern in patterns:
        matches = sorted(glob.glob(pattern), reverse=True)
        if matches:
            return matches[0]
    return None


def npm_env(npm: str):
    # npm.cmd necesita encontrar node.exe en el PATH
    env = os.environ.copy()
    env['PATH'] = str(Path(npm).parent) + os.pathsep + env.get('PATH', '')
    return env


def port_in_use(port: int) -> bool:
    # IPv4 e IPv6: en Windows, Node/Vite escucha "localhost" en ::1
    for family, host in ((socket.AF_INET, '127.0.0.1'), (socket.AF_INET6, '::1')):
        try:
            with socket.socket(family) as s:
                s.settimeout(0.5)
                if s.connect_ex((host, port)) == 0:
                    return True
        except OSError:
            continue
    return False


def install_frontend(npm: str):
    """npm ci solo si package-lock.json cambió desde la última instalación."""
    lock = FRONTEND / 'package-lock.json'
    marker = FRONTEND / 'node_modules' / '.gestorpro-lock'
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    if marker.exists() and marker.read_text(encoding='utf-8').strip() == digest:
        say('  Dependencias del frontend al día.')
        return
    result = run([npm, 'ci', '--no-audit', '--no-fund'], cwd=FRONTEND, env=npm_env(npm), check=False)
    if result.returncode != 0:
        fail('No se pudieron instalar las dependencias del frontend.\n'
             '  Si el error dice EPERM o "operation not permitted", hay archivos en uso:\n'
             '  cierra las ventanas del backend y del frontend que abrió iniciar.bat\n'
             '  (y cualquier editor abierto en la carpeta frontend) y vuelve a ejecutar instalar.bat.')
    marker.write_text(digest, encoding='utf-8')


# ── .env y base de datos ────────────────────────────────────────────────────

def env_is_managed() -> bool:
    return ENV_FILE.exists() and MANAGED_MARK in ENV_FILE.read_text(encoding='utf-8')


def ensure_env():
    if ENV_FILE.exists():
        say('  .env ya existe: se respeta tu configuración.' if not env_is_managed()
            else '  .env ya existe (gestionado por este script).')
        return
    secret = secrets.token_urlsafe(50)
    ENV_FILE.write_text(f"""{MANAGED_MARK}
# Configuración LOCAL de desarrollo. No subir al repositorio.
SECRET_KEY={secret}
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://postgres@localhost:{PG_PORT}/{DB_NAME}
CORS_ALLOWED_ORIGINS=http://localhost:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173
FRONTEND_URL=http://localhost:5173
DEFAULT_PLAN_CODE=starter
THROTTLE_AUTH=30/min
GROQ_API_KEY=
""", encoding='utf-8')
    say(f'  .env creado (base de datos local en el puerto {PG_PORT}).')


def ensure_postgres(pg_bin: Path):
    """Inicializa y arranca el clúster local de este script (solo si .env lo gestiona el script)."""
    pg_ctl, initdb = str(pg_bin / f'pg_ctl{EXE}'), str(pg_bin / f'initdb{EXE}')
    if not (PG_DATA / 'PG_VERSION').exists():
        say(f'  Creando la base de datos local en {PG_DATA} ...')
        # trust + listen_addresses=localhost: sin contraseña, pero solo desde este equipo
        run([initdb, '-D', str(PG_DATA), '-U', 'postgres', '-A', 'trust', '-E', 'UTF8', '--no-locale'], capture=True)
    status = run([pg_ctl, 'status', '-D', str(PG_DATA)], check=False, capture=True)
    if status.returncode == 0:
        say('  PostgreSQL ya está en marcha.')
    else:
        if port_in_use(PG_PORT):
            fail(f'El puerto {PG_PORT} está ocupado por otro programa. Define GESTORPRO_PG_PORT con otro puerto.')
        say(f'  Arrancando PostgreSQL en el puerto {PG_PORT} ...')
        # Sin capturar la salida: en Windows el servidor hereda las tuberías y
        # el script esperaría para siempre a que se cerraran.
        started = subprocess.run(
            [pg_ctl, 'start', '-D', str(PG_DATA), '-l', str(PG_DATA / 'server.log'), '-w', '-t', '60',
             '-o', f'-p {PG_PORT} -c listen_addresses=localhost'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if started.returncode != 0:
            log = PG_DATA / 'server.log'
            tail = log.read_text(encoding='utf-8', errors='replace').splitlines()[-15:] if log.exists() else []
            fail('PostgreSQL no arrancó. Últimas líneas del registro:\n  ' + '\n  '.join(tail))
    psql = str(pg_bin / f'psql{EXE}')
    exists = run([psql, '-h', 'localhost', '-p', str(PG_PORT), '-U', 'postgres', '-tAc',
                  f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'"], capture=True).stdout.strip()
    if exists != '1':
        run([str(pg_bin / f'createdb{EXE}'), '-h', 'localhost', '-p', str(PG_PORT), '-U', 'postgres', DB_NAME],
            capture=True)
        say(f'  Base de datos "{DB_NAME}" creada.')


def require_postgres():
    if not env_is_managed():
        return  # el usuario gestiona su propio PostgreSQL (su .env)
    pg_bin = find_pg_bin()
    if pg_bin is None:
        fail('No encontré PostgreSQL.\n'
             '  Descarga los binarios (zip) desde https://www.enterprisedb.com/download-postgresql-binaries,\n'
             f'  descomprímelos en {Path.home() / "pgsql"} y vuelve a ejecutar.\n'
             '  O indica la carpeta "bin" con:  set PG_BIN=C:\\ruta\\a\\pgsql\\bin')
    say(f'  PostgreSQL: {pg_bin}')
    ensure_postgres(pg_bin)


def require_npm() -> str:
    npm = find_npm()
    if npm is None:
        fail('No encontré Node.js.\n'
             '  Descarga el zip de https://nodejs.org (Windows x64), descomprímelo en tu carpeta de usuario\n'
             f'  ({Path.home()}) y vuelve a ejecutar.')
    say(f'  Node.js: {Path(npm).parent}')
    return npm


# ── Comandos ────────────────────────────────────────────────────────────────

def git_pull():
    if not shutil.which('git') or not (ROOT / '.git').exists():
        return
    dirty = run(['git', 'status', '--porcelain', '--untracked-files=no'], capture=True, check=False).stdout.strip()
    if dirty:
        say('  Hay cambios locales sin guardar en git: no se actualiza el código.')
        return
    branch = run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], capture=True).stdout.strip()
    say(f'  Actualizando la rama {branch} ...')
    result = run(['git', 'pull', '--ff-only', 'origin', branch], capture=True, check=False)
    say('  Código al día.' if result.returncode == 0
        else '  No se pudo actualizar (¿sin internet?). Sigo con lo que hay.')


def setup():
    step('1/6  Código')
    git_pull()
    step('2/6  Configuración')
    ensure_env()
    step('3/6  Base de datos')
    require_postgres()
    step('4/6  Frontend (puede tardar unos minutos la primera vez)')
    npm = require_npm()
    install_frontend(npm)
    step('5/6  Migraciones')
    manage('migrate')
    step('6/6  Datos de prueba')
    demo_exists = manage('shell', '-c', "from gestorpro.core.tenancy.models import Tenant;"
                         "print(Tenant.objects.filter(name='Panadería La Espiga (demo)').exists())",
                         capture=True).stdout.strip().endswith('True')
    if demo_exists:
        say('  La panadería demo ya existe (propietaria@demo.miga.co / cajero@demo.miga.co).')
    else:
        password = input('  Contraseña para los usuarios demo (Enter = Demo-Miga-2026): ').strip() or 'Demo-Miga-2026'
        manage('seed_demo', '--password', password)

    favorita_exists = manage('shell', '-c', "from gestorpro.core.tenancy.models import Tenant;"
                             "print(Tenant.objects.filter(slug='panaderia-la-favorita').exists())",
                             capture=True).stdout.strip().endswith('True')
    if not favorita_exists:
        email = input('\n  ¿Crear "Panadería La Favorita"? Escribe el email del dueño (Enter para omitir): ').strip()
        if email:
            manage('onboard_tenant', 'Panadería La Favorita', email, '--plan', 'business', '--city', 'Bogotá')
            manage('load_starter_catalog', 'panaderia-la-favorita')
            say('  Abre el enlace de arriba (con iniciar.bat en marcha) para definir la contraseña del dueño.')
    say('\nListo. Ahora ejecuta iniciar.bat')


def wait_for(port: int, seconds: int) -> bool:
    for _ in range(seconds):
        if port_in_use(port):
            return True
        time.sleep(1)
    return False


def start():
    step('Base de datos')
    require_postgres()
    # Por si se actualizó el código sin ejecutar instalar.bat
    if manage('migrate', '--noinput', capture=True, check=False).returncode != 0:
        fail('No se pudieron aplicar las migraciones. Ejecuta instalar.bat y revisa el mensaje.')
    for port, what in [(8000, 'el backend'), (5173, 'el frontend')]:
        if port_in_use(port):
            fail(f'El puerto {port} ya está en uso (¿otro proyecto o una ventana anterior abierta?).\n'
                 f'  Ciérralo y vuelve a intentar: {what} de GestorPro necesita ese puerto.')
    npm = require_npm()
    new_console = {'creationflags': subprocess.CREATE_NEW_CONSOLE} if IS_WINDOWS else {}
    step('Backend  → http://localhost:8000  (se abre en otra ventana)')
    subprocess.Popen([venv_python(), 'manage.py', 'runserver', '8000'], cwd=ROOT, **new_console)
    step('Frontend → http://localhost:5173  (se abre en otra ventana)')
    subprocess.Popen([npm, 'run', 'dev'], cwd=FRONTEND, env=npm_env(npm), **new_console)
    if wait_for(8000, 40) and wait_for(5173, 60):
        webbrowser.open('http://localhost:5173')
        say('\nGestorPro está corriendo. Para detenerlo, cierra las dos ventanas que se abrieron.')
    else:
        fail('No arrancó a tiempo. Revisa los mensajes en las ventanas del backend y del frontend.')


if __name__ == '__main__':
    os.environ.setdefault('PYTHONUTF8', '1')  # acentos correctos en la consola de Windows
    commands = {'setup': setup, 'start': start}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        fail('Uso: python scripts/dev_local.py setup|start')
    commands[sys.argv[1]]()
