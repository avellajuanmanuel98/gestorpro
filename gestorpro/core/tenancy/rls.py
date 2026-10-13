"""
Row-Level Security (RLS) de PostgreSQL: la última red del aislamiento entre empresas.

Las capas de aplicación (manager fail-closed, save() con verificación de FKs,
permisos) ya impiden ver o escribir datos de otra empresa. RLS repite esa regla
DENTRO de PostgreSQL, para que un error futuro en el código (una consulta cruda,
un acceso por relación con el manager base, un `all_tenants` mal usado) no pueda
saltársela:

  Cada tabla de un TenantModel tiene la política `gestorpro_tenant_isolation`:
  una fila solo es visible y escribible si su `tenant_id` es la empresa activa
  de la sesión de base de datos, o si la sesión declaró explícitamente un acceso
  global (plataforma, autenticación, migraciones).

  Sin empresa activa y sin acceso global declarado, NO hay filas (fail-closed).

Cómo se aplica:

- La aplicación no consulta como dueña de las tablas (el dueño y los
  superusuarios se saltan RLS), sino con el rol `gestorpro_rls`: sin login, sin
  superusuario, sin BYPASSRLS. Al abrir cada conexión se hace SET ROLE a él.
  Las migraciones y las copias de seguridad sí corren como dueño.
- Antes de cada consulta, un "execute wrapper" sincroniza con la sesión de
  PostgreSQL la empresa activa (ContextVar de tenancy.context) y el acceso
  global (`rls_bypass()`). Solo se envía cuando cambia; y como esos valores son
  transaccionales en PostgreSQL (un ROLLBACK los revierte), se vuelven a enviar
  si la transacción o el savepoint donde se fijaron se revirtió.
- Solo `migrate`, `flush`, `makemigrations` y `showmigrations` corren como dueño
  (mantenimiento declarado).
- post_migrate crea el rol si se puede, le da permisos de lectura/escritura
  (nunca TRUNCATE ni DDL) y crea o actualiza las políticas de TODOS los
  TenantModel: un modelo nuevo queda protegido sin escribir nada.

Settings:
  GESTORPRO_RLS_REQUIRED (True): si la conexión no puede usar el rol
  `gestorpro_rls`, toda consulta con empresa activa o acceso global falla en
  lugar de seguir sin RLS.
"""
from contextlib import contextmanager
from contextvars import ContextVar

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connections

from .context import get_active_tenant_id

APP_ROLE = 'gestorpro_rls'
POLICY = 'gestorpro_tenant_isolation'
FUNCTION = 'gestorpro_tenant_visible'

_bypass: ContextVar[bool] = ContextVar('gestorpro_rls_bypass', default=False)
_maintenance: ContextVar[bool] = ContextVar('gestorpro_rls_maintenance', default=False)


@contextmanager
def rls_bypass():
    """
    Acceso global DECLARADO (todas las empresas). Solo para la plataforma, la
    autenticación y procesos internos, y siempre junto a su propio control de
    acceso: esto abre la red de PostgreSQL, no los permisos de la aplicación.
    """
    token = _bypass.set(True)
    try:
        yield
    finally:
        _bypass.reset(token)


class _Reset:
    def __init__(self, token):
        self.token = token

    def restore(self):
        _bypass.reset(self.token)


def reset_global_access() -> _Reset:
    """Empieza sin acceso global (cada petición); `.restore()` deja el estado previo."""
    return _Reset(_bypass.set(False))


def bypass_active() -> bool:
    return _bypass.get() or _maintenance.get()


@contextmanager
def maintenance():
    """Migraciones y mantenimiento: la conexión vuelve a su usuario (dueño) y sin filtro."""
    token = _maintenance.set(True)
    try:
        yield
    finally:
        _maintenance.reset(token)


# ── Sincronización por consulta ─────────────────────────────────────────────

class _Applied:
    """Marca de que los valores se fijaron dentro de una transacción (on_commit la confirma)."""

    def __init__(self):
        self.committed = False

    def __call__(self):
        self.committed = True


def _desired(conn) -> tuple[str, str, str]:
    if _maintenance.get():
        return ('none', '', 'on')
    tenant_id = get_active_tenant_id(required=False)
    bypass = _bypass.get()
    if conn._gestorpro_rls_can_use_role:
        role = APP_ROLE
    elif (tenant_id is not None or bypass) and getattr(settings, 'GESTORPRO_RLS_REQUIRED', True):
        # Con datos de empresa en juego, sin RLS no se sigue. (Sin empresa ni acceso global,
        # como al instalar la base, no hay filas de empresa que proteger: el manager no las lee.)
        raise ImproperlyConfigured(
            f'La conexión a PostgreSQL no puede usar el rol "{APP_ROLE}": sin él no hay Row-Level Security. '
            f'Ejecuta "manage.py migrate" con un usuario que pueda crearlo, o créalo a mano '
            f'(CREATE ROLE {APP_ROLE} NOLOGIN; GRANT {APP_ROLE} TO <usuario de la app>).')
    else:
        role = 'none'
    if bypass:
        return (role, '', 'on')
    return (role, '' if tenant_id is None else str(tenant_id), 'off')


def _still_applied(conn, state, desired) -> bool:
    if state is None or state[0] != desired:
        return False
    marker = state[1]
    if marker is None or marker.committed:
        return True
    # Fijados dentro de una transacción aún abierta: siguen vigentes mientras ni la
    # transacción ni el savepoint donde se fijaron se hayan revertido (Django quita
    # de run_on_commit lo registrado dentro de lo que se revierte).
    return any(func is marker for _sids, func, _robust in conn.run_on_commit)


def _sync(execute, sql, params, many, context):
    conn = context['connection']
    desired = _desired(conn)
    if not _still_applied(conn, getattr(conn, '_gestorpro_rls_state', None), desired):
        context['cursor'].cursor.execute(
            "SELECT set_config('role', %s, false), set_config('gestorpro.tenant_id', %s, false), "
            "set_config('gestorpro.rls_bypass', %s, false)", desired)
        marker = None
        if conn.in_atomic_block:
            marker = _Applied()
            conn.on_commit(marker)
        conn._gestorpro_rls_state = (desired, marker)
    return execute(sql, params, many, context)


def on_connection_created(sender, connection, **kwargs):
    if connection.vendor != 'postgresql':
        return
    with connection.connection.cursor() as cursor:
        cursor.execute('SELECT pg_has_role(session_user, %s, %s) FROM pg_roles WHERE rolname = %s',
                       [APP_ROLE, 'MEMBER', APP_ROLE])
        row = cursor.fetchone()
    connection._gestorpro_rls_can_use_role = bool(row and row[0])
    connection._gestorpro_rls_state = None
    if _sync not in connection.execute_wrappers:
        connection.execute_wrappers.append(_sync)


# ── Instalación (post_migrate) ──────────────────────────────────────────────

def tenant_tables() -> list[str]:
    from .db import TenantModel

    return sorted({m._meta.db_table for m in apps.get_models()
                   if issubclass(m, TenantModel) and not m._meta.proxy and m._meta.managed})


def install(using='default') -> None:
    """Idempotente: rol, permisos, función y políticas de todas las tablas de empresa."""
    conn = connections[using]
    if conn.vendor != 'postgresql':
        return
    with maintenance(), conn.cursor() as cursor:
        cursor.execute('SELECT rolsuper OR rolcreaterole FROM pg_roles WHERE rolname = current_user')
        can_create = cursor.fetchone()[0]
        cursor.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', [APP_ROLE])
        if cursor.fetchone() is None and can_create:
            cursor.execute(f'CREATE ROLE {APP_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE')
        cursor.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', [APP_ROLE])
        role_exists = cursor.fetchone() is not None
        if role_exists:
            # Lectura y escritura de filas; nunca TRUNCATE, DDL ni dueño de nada
            cursor.execute(f'GRANT USAGE ON SCHEMA public TO {APP_ROLE}')
            cursor.execute(f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE}')
            cursor.execute(f'GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}')
        cursor.execute(f"""
            CREATE OR REPLACE FUNCTION {FUNCTION}(row_tenant bigint) RETURNS boolean
            LANGUAGE sql STABLE AS $$
                SELECT current_setting('gestorpro.rls_bypass', true) = 'on'
                    OR row_tenant = nullif(current_setting('gestorpro.tenant_id', true), '')::bigint
            $$""")
        for table in tenant_tables():
            quoted = conn.ops.quote_name(table)
            cursor.execute(f'ALTER TABLE {quoted} ENABLE ROW LEVEL SECURITY')
            cursor.execute(f'DROP POLICY IF EXISTS {POLICY} ON {quoted}')
            cursor.execute(f'CREATE POLICY {POLICY} ON {quoted} USING ({FUNCTION}(tenant_id)) '
                           f'WITH CHECK ({FUNCTION}(tenant_id))')
    # La conexión actual ya puede usar el rol si se acaba de crear
    if hasattr(conn, '_gestorpro_rls_can_use_role') and role_exists:
        on_connection_created(None, conn)
    if getattr(settings, 'GESTORPRO_RLS_REQUIRED', True) and not getattr(conn, '_gestorpro_rls_can_use_role', False):
        # Mejor un despliegue detenido con un mensaje claro que una app en marcha sin esta red
        raise ImproperlyConfigured(
            f'Row-Level Security: el usuario de la base no puede usar el rol "{APP_ROLE}" y no tiene permiso para '
            f'crearlo. Como administrador de PostgreSQL: CREATE ROLE {APP_ROLE} NOLOGIN; '
            f'GRANT {APP_ROLE} TO <usuario de la app>; y vuelve a ejecutar migrate.')


def on_post_migrate(sender, using='default', **kwargs):
    install(using)


def maintenance_command(command_class):
    """Hace que un comando de manage.py corra como dueño de la base (mantenimiento)."""
    original = command_class.handle
    if getattr(original, '_gestorpro_maintenance', False):
        return

    def handle(self, *args, **kwargs):
        with maintenance():
            return original(self, *args, **kwargs)

    handle._gestorpro_maintenance = True
    command_class.handle = handle
