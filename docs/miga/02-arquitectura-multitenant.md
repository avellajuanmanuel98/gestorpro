# Documento 02 — Arquitectura multi-tenant (Fases 0, 2 y 3)

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-10-08 |
| **Depende de** | [01 — Auditoría y arquitectura](01-auditoria-y-arquitectura.md) |

Este documento describe **cómo funciona hoy** el aislamiento entre empresas y qué reglas debe seguir todo módulo nuevo. Es la referencia para Core, Capabilities, Verticals (Miga) y Platform.

---

## 1. Capas del código

```
gestorpro/
├── kernel/          Sin dominio: dinero (money.py), paginación, errores, manejo de excepciones
├── core/            Común a cualquier PYME
│   ├── tenancy/     Tenant, Location (sucursal), contexto de tenant, TenantModel
│   ├── identity/    User global, login/logout/refresh, cambio de empresa, registro
│   ├── access/      Permission (catálogo), Role, Membership, permisos DRF, alta de empresas
│   ├── api/         Bases de vistas/serializers para recursos de empresa
│   ├── customers/   suppliers/   catalog/   billing/   reporting/
├── capabilities/    Reutilizables y opcionales: hr (personal), assistant (IA)
├── verticals/
│   └── bakery/      Miga: definición del vertical y datos demo
└── platform/
    └── admin_panel/ Consola interna de GestorPro (/admin/)
```

**Reglas de dependencia** (verificadas en CI con `lint-imports`, configuración en `pyproject.toml`):

- `platform` y `verticals` → pueden importar `capabilities`, `core`, `kernel`. Son independientes entre sí.
- `capabilities` → `core`, `kernel`. Las capabilities no se importan entre sí.
- `core` → `kernel`. **Nunca** importa capabilities, verticals ni platform.

Comprobado: añadir un `import` de `capabilities` dentro de `core` hace fallar el CI.

---

## 2. Multi-tenancy fail-closed

**Estrategia:** base de datos y schema compartidos, columna `tenant_id` en cada tabla de negocio y **aislamiento aplicado en varias capas independientes**. La justificación (frente a schema-per-tenant o BD-per-tenant) está en el Documento 01, §11.

### 2.1 Capas implementadas

| # | Capa | Dónde | Qué impide |
|---|---|---|---|
| 1 | **Autenticación con verificación de membresía** | `core/identity/authentication.py` | Que un token siga dando acceso tras suspender al usuario o a la empresa. El JWT lleva `tid` (empresa activa) y **en cada petición** se comprueba en BD que la membresía y la empresa siguen activas. |
| 2 | **Contexto de tenant por petición** | `core/tenancy/context.py`, `middleware.py` | Que el tenant de una petición se filtre a la siguiente cuando gunicorn reutiliza un hilo. Cada petición empieza sin tenant y el contexto se restablece al terminar. |
| 3 | **Manager por defecto que falla cerrado** | `core/tenancy/db.py` (`TenantModel.objects`) | Leer datos sin empresa activa: lanza `TenantContextMissing` en lugar de devolver todo. Con empresa activa, filtra siempre por ella. |
| 4 | **FKs resueltas dentro del tenant** | consecuencia de la capa 3 | Referenciar datos ajenos (S1). Los serializers de DRF resuelven las FKs con el manager por defecto del modelo relacionado: un ID de otra empresa simplemente "no existe" → 400. |
| 5 | **Integridad en escritura** | `TenantModel.save()/delete()` y `bulk_create` | Escribir sin empresa activa, escribir en otra empresa o guardar una FK que apunte a otra empresa, aunque el objeto se haya cargado por otra vía. |
| 6 | **Unicidad por empresa** | `UniqueConstraint(fields=['tenant', ...])` | Que la unicidad filtre o bloquee datos de otra empresa (S2). |
| 7 | **Permisos por método HTTP** | `core/access/permissions.py` | Acceder sin permiso explícito. Un método sin permiso declarado se deniega. |
| 8 | **Guardianes en CI** | `tests/architecture/` | Que un módulo nuevo olvide heredar `TenantModel` o declarar permisos. |

Pendiente (Fase 12): **Row-Level Security de PostgreSQL** como red final a nivel de motor y claves foráneas compuestas `(tenant_id, id)`.

### 2.2 Acceso sin filtro

`Modelo.all_tenants` es el **único** acceso global. Hoy solo lo usan:

- la autenticación (`access.services.active_memberships_for`), para validar membresías antes de que exista un tenant activo;
- el panel de plataforma (`platform/admin_panel`), de solo lectura para modelos con tenant;
- la verificación de integridad de FKs en `TenantModel.check_tenant_relations`.

Cualquier uso nuevo de `all_tenants` debe justificarse en la revisión de código.

### 2.3 Código fuera de una petición HTTP

Comandos, tareas o scripts deben activar explícitamente la empresa:

```python
from gestorpro.core.tenancy.context import tenant_context

with tenant_context(tenant):
    Customer.objects.create(first_name='Ana')
```

Sin ese bloque, cualquier consulta o escritura de negocio falla.

---

## 3. Usuarios, empresas y roles

```
User (identidad global)
  └─< Membership (tenant, role, status, default_location)
         └─ Role (por empresa) ─< permisos (catálogo en código)
Tenant ─< Location (sucursales; "Principal" se crea con la empresa)
```

- **Multiempresa desde el inicio:** un usuario puede pertenecer a varias empresas con un rol distinto en cada una. `POST /api/auth/switch-tenant/` emite tokens para otra empresa y revoca el refresh anterior.
- **Sucursales desde el inicio:** `Location` existe aunque hoy la UI no la explote. Caja, inventario y ventas se registrarán por sucursal; añadir esa dimensión después obligaría a migrar todos los documentos.
- **Roles de sistema** (creados con cada empresa, `core/access/defaults.py`): `OWNER` (todos los permisos, incluidos los futuros), `ADMIN`, `SUPERVISOR`, `CASHIER`, `INVENTORY`. Cada empresa podrá crear roles propios (UI en la Fase 4).
- **Catálogo de permisos:** cada módulo declara los suyos en `<módulo>/permissions.py`. Se sincronizan a BD tras `migrate`. Agregar un módulo no requiere editar listas centrales.
- **Super Admin de plataforma:** `User.is_platform_admin`. No tiene membresías y **no puede leer datos de ninguna empresa por la API** (verificado por test). Usa `/admin/`, que muestra empresas, usuarios, membresías y roles, pero no clientes, facturas ni otros datos de negocio. Las empresas no se pueden borrar desde allí: se suspenden.

### 3.1 Sesión y tokens

| Endpoint | Uso |
|---|---|
| `POST /api/auth/register/` | Crea cuenta + empresa (OWNER) y devuelve tokens. |
| `POST /api/auth/login/` | Tokens para la última empresa usada. Limitado a `THROTTLE_AUTH` (10/min por IP). |
| `POST /api/auth/token/refresh/` | Rota el refresh; el anterior queda revocado. |
| `POST /api/auth/logout/` | Revoca el refresh token. |
| `GET /api/auth/me/` | Usuario, empresa activa, rol, permisos y membresías. |
| `POST /api/auth/switch-tenant/` | Cambia de empresa. |
| `POST /api/auth/change-password/` | Cambia la contraseña y revoca todas las sesiones. |

Access token: 15 minutos. Refresh: 7 días, con rotación y lista negra. El frontend usa un **refresh de un solo vuelo**: si varias peticiones reciben 401 a la vez, esperan una única renovación, porque con rotación y lista negra la segunda fallaría.

Pendiente (Fase 12): mover el refresh token a cookie `httpOnly` y quitarlo de `localStorage`.

---

## 4. Cómo construir un módulo de negocio nuevo

1. Crear la app en la capa correcta (`core/`, `capabilities/` o `verticals/<vertical>/`) con `label` explícito en `apps.py`.
2. Modelos que heredan **`TenantModel`** (o `AuthoredTenantModel` si guardan autor). Toda restricción única incluye `tenant`.
3. `permissions.py` con `PERMISSIONS = {'modulo.accion': 'Descripción'}` y, si aplica, añadir los patrones a los roles de sistema en `core/access/defaults.py`.
4. Serializers que heredan **`TenantModelSerializer`**.
5. Vistas sobre **`TenantListCreateView` / `TenantDetailView`** (o `HasTenantPermission` en `APIView`), declarando `model` y `required_permissions` por método.
6. Lógica que toca varias entidades → función en `services.py` con `@transaction.atomic` y `select_for_update` sobre lo que se modifica. Nada de reglas de negocio en `Model.save()` ni en serializers.
7. Dinero con `gestorpro.kernel.money` (`money`, `percentage_of`, `money_str`). **Nunca `float`.**
8. Tests: los guardianes de `tests/architecture/` validan los pasos 2 y 5 automáticamente. Añadir tests de aislamiento si el módulo introduce relaciones nuevas entre entidades.

---

## 5. Dinero

- Modelos: `DecimalField(14, 2)` para importes y `DecimalField(12, 3)` para cantidades.
- Un único redondeo: `ROUND_HALF_UP` a centavos, por línea (`kernel/money.py`). `money()` rechaza `float`.
- API: los importes viajan como **string decimal** (`"1469.11"`). El frontend solo los convierte a número para dibujar gráficos (`lib/money.ts → toDisplayNumber`).
- **El servidor calcula los totales.** En facturación, precio e impuesto salen del catálogo. Cambiar el precio exige `billing.override_price` y aplicar descuentos exige `billing.apply_discount`. El impuesto no lo puede definir el cliente. Un documento pagado o cancelado no se puede modificar, y solo se pueden borrar borradores.

El **costo promedio ponderado** y el libro de movimientos de inventario se documentarán con su implementación (Fase 8).

---

## 6. Despliegue

- `Procfile`: `migrate` → `collectstatic` → `gunicorn`, todo con `config.settings.prod`. **No existe ningún comando que borre la base de datos** y un test lo verifica (`tests/isolation/test_deploy_safety.py`).
- `seed_demo` solo corre con `DEBUG=True`, nunca crea superusuarios y no tiene contraseñas fijas.
- `config/settings/prod.py` exige una `SECRET_KEY` de ≥ 50 caracteres y activa HTTPS, HSTS y cookies seguras.
- Solo PostgreSQL. En local: `docker compose up -d db`.

### ⚠️ Paso manual único antes de desplegar esta rama

El historial de migraciones se regeneró desde cero (aprobado en D-1: solo había ~20 registros de prueba). La base de datos actual de Railway tiene el esquema anterior, y `migrate` fallará con `InconsistentMigrationHistory` **sin tocar ningún dato**: es un fallo seguro.

Para desplegar hay que **reemplazar la base de datos de Railway por una vacía una sola vez**, desde el panel de Railway (crear un servicio PostgreSQL nuevo y apuntar `DATABASE_URL` a él, o borrar y recrear el volumen del existente). Es una acción manual y deliberada: no hay ningún mecanismo automático que lo haga.

---

## 7. Qué queda fuera de estas fases

| Tema | Fase |
|---|---|
| Auditoría (`AuditLog`) de login, permisos, precios, etc. | 4 |
| UI de usuarios, invitaciones y roles personalizados | 4 |
| Planes, suscripciones y límites (Platform) | 4 (modelo) / 10 (UI) |
| Unificación visual de las páginas heredadas + combobox con búsqueda | 5 |
| `Item` (producto terminado / materia prima), unidades, libro de inventario, costo promedio | 6 y 8 |
| POS y caja | 7 |
| Dashboard y analítica de Miga | 9 |
| Row-Level Security, refresh en cookie `httpOnly`, revisión OWASP | 12 |
| Facturación electrónica DIAN (tras validar con un asesor tributario) | posterior |
