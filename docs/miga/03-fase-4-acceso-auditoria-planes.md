# Documento 03 — Fase 4: auditoría, usuarios y roles, planes

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-10-09 |
| **Depende de** | [02 — Arquitectura multi-tenant](02-arquitectura-multitenant.md) |

---

## 1. Auditoría (`core/audit`)

Hay dos registros, ambos **de solo inserción**:

| Modelo | Alcance | Quién lo ve | Qué guarda |
|---|---|---|---|
| `AuditLog` | Empresa (`TenantModel`) | Usuarios con `audit.view` (OWNER, ADMIN) en `/audit` | Acciones dentro de la empresa |
| `SecurityEvent` | Global | Personal de GestorPro en `/admin/` | Login exitoso y fallido, logout, cambio de contraseña, cambio de empresa, invitación aceptada |

**Inmutabilidad.** El ORM rechaza `save()` sobre filas existentes, `delete()` y `QuerySet.update()/delete()`. Además, un **trigger de PostgreSQL** rechaza cualquier `UPDATE`, incluso por SQL directo (migración `audit/0002`). `DELETE` no se bloquea en el motor solo para permitir, en el futuro, la baja completa de una empresa por la plataforma.

**Cada registro guarda:** actor (id y email en ese momento), acción, entidad e id, resumen legible en español, cambios `{campo: [antes, después]}`, IP y user agent. La IP se toma del proxy de confianza (`AUDIT_TRUSTED_PROXY_COUNT=1` en producción), no de lo que envía el cliente.

**Qué se audita hoy:**

- **CRUD de todos los módulos.** Lo hacen automáticamente las vistas base (`core/api/views.py`), en la **misma transacción** que el cambio: si la operación falla, no queda registro, y si el registro falla, no se aplica el cambio.
- **Eventos dedicados:**
  - cambio de precio o de IVA de un producto (`audit_field_events` en el modelo);
  - cambio de estado de una factura;
  - login y logout, cambio de empresa y de contraseña;
  - alta de empresa;
  - invitaciones, cambios de rol y de estado, bajas de miembros;
  - creación, edición y borrado de roles.
- **Campos sensibles enmascarados:** el salario (`audit_sensitive_fields`). Se registra que cambió, no su valor.

Para que un módulo nuevo audite eventos propios: `audit.record('modulo.entidad.accion', target=obj, summary='...', changes={...})`.

---

## 2. Usuarios, invitaciones y roles (`core/access`)

### Invitaciones

1. Un usuario con `access.manage_users` invita a un email con un rol.
2. Se genera un **token aleatorio de 256 bits**. En la base de datos solo se guarda su **SHA-256**: el enlace se muestra **una sola vez**.
3. El enlace vence en **7 días**. Puede revocarse, y crear una invitación nueva para el mismo email revoca la anterior.
4. Al aceptar:
   - si el email **no tiene cuenta**, se crea, validando la contraseña con las reglas de Django;
   - si **ya tiene cuenta**, debe **demostrar su identidad con su contraseña**, y queda como usuario multiempresa.

Todavía no hay envío de correo: quien invita copia el enlace y lo comparte por el medio que prefiera (por ejemplo, WhatsApp). La infraestructura de correo se integrará más adelante sin cambiar el modelo.

### Reglas de seguridad (aplicadas en el backend, con tests)

- **Anti-escalada:** nadie puede asignar un rol ni crear o editar un rol con permisos que no tiene. Solo OWNER está exento, porque los tiene todos.
- Solo un OWNER puede asignar el rol OWNER o modificar a otro OWNER.
- Nadie puede modificar ni quitar su propio acceso, para evitar auto-bloqueos.
- Siempre queda al menos un OWNER activo (defensa en profundidad del servicio).
- Suspender a alguien corta su acceso **en la siguiente petición**, porque la membresía se verifica en cada request.
- El rol OWNER no se puede modificar. Los roles del sistema no se pueden renombrar ni borrar, pero sí ajustar sus permisos.
- Un rol con usuarios o invitaciones pendientes no se puede borrar.

### Permisos nuevos

`access.view`, `access.manage_users`, `access.manage_roles`, `audit.view`. Los permisos `tenant.*` pasan a declararse en el módulo de empresa (`tenancy`).

Las **métricas financieras del dashboard** (`billing/summary`, `billing/monthly-revenue`) ahora exigen `reports.view`, no solo `billing.view`: el cajero ya no ve el total recaudado ni la cartera.

---

## 3. Planes y suscripciones (`platform/subscriptions`)

```
Plan ─< PlanFeature (clave)      Subscription (1 por empresa): plan, estado,
     └< PlanLimit (clave, valor)   inicio, fin de prueba, fin de período, ref. de pago
```

**Las restricciones son datos, no código.** Las claves válidas están en `core/entitlements.py`:

| Funcionalidad | Qué habilita |
|---|---|
| `module.hr` | Módulo de personal (empleados, reporte de RR. HH.) |
| `module.assistant` | Asistente de IA |
| `custom_roles` | Crear roles personalizados |

| Límite | Qué cuenta |
|---|---|
| `users` | Miembros activos + invitaciones pendientes |
| `locations` | Sucursales activas |
| `products` | Productos del catálogo |
| `custom_roles` | Roles personalizados |

### Planes sembrados (propuesta editable desde `/admin/` → Planes)

| | Starter | Business | Pro |
|---|---|---|---|
| Usuarios | 3 | 10 | ilimitado |
| Sucursales | 1 | 2 | 5 |
| Productos | 150 | 1.000 | ilimitado |
| Roles personalizados | — | 3 | ilimitado |
| Personal (RR. HH.) | — | ✓ | ✓ |
| Asistente IA | — | — | ✓ |
| Precio | por definir | por definir | por definir |

Los **precios están vacíos a propósito**: es una decisión de negocio tuya. No hay cobro real todavía. `Subscription.external_ref` queda reservado para la pasarela de pagos.

### Cómo se conecta sin acoplar capas

- El **Core** solo conoce `core/entitlements.py`: una interfaz con `for_tenant()`, `require_feature()` y `check_limit()`, más un proveedor registrable. **Fail-closed:** sin proveedor o sin suscripción, no hay funcionalidades opcionales y todos los límites valen 0.
- **Platform** registra el proveedor al arrancar y crea la suscripción al escuchar la señal `tenant_provisioned`.
- Las vistas declaran `required_feature = 'module.hr'`, y `HasTenantPermission` lo exige (403 `feature_not_in_plan`).
- `/api/auth/me/` devuelve `plan` y `features` para adaptar la interfaz, y `/api/tenant/plan/` devuelve el consumo de cada límite.
- **Empresas nuevas:** arrancan en **prueba de 14 días** del plan `DEFAULT_PLAN_CODE` (por defecto `starter`).
- **Estado de la suscripción:** hoy solo `canceled` revoca las funcionalidades. El cobro y el bloqueo por falta de pago llegarán con la integración de pagos.

---

## 4. Vertical Miga

`verticals/bakery/definition.py` define `VerticalDefinition(key, brand, default_categories, recommended_plan)`. Al dar de alta una empresa con `vertical='bakery'`, el vertical crea sus categorías por defecto (Panes, Panes rellenos, Hojaldres…). Escucha la misma señal `tenant_provisioned`: el Core no sabe que existen verticales.

---

## 5. Frontend

| Pantalla | Ruta | Requiere |
|---|---|---|
| Usuarios: lista, invitar (enlace copiable), cambiar rol, suspender/reactivar, quitar, invitaciones pendientes | `/users` | `access.view` (gestionar: `access.manage_users`) |
| Roles: editor de permisos por módulo; marca lo no incluido en el plan y lo que el usuario no puede otorgar | `/roles` | `access.view` (editar: `access.manage_roles`; crear: plan con `custom_roles`) |
| Auditoría: filtros por tipo de acción y fechas, detalle de cambios, paginación | `/audit` | `audit.view` |
| Aceptar invitación (pública) | `/invitation/:token` | — |
| Mi Empresa: plan, estado de prueba y consumo de límites | `/company` | `tenant.view` |

**Componentes nuevos del kit:** `ConfirmDialog` (reemplaza a `confirm()` en las pantallas nuevas), `Select` y `PageHeader`.

**Corrección de accesibilidad:** `Input` y `Select` ahora asocian la etiqueta al campo (`htmlFor`/`id`, `aria-describedby`, `aria-invalid`). Afecta a todos los formularios que los usan.

La navegación oculta los módulos que el plan no incluye (por ejemplo, Empleados en Starter) y el botón del asistente IA si el plan no lo tiene.

---

## 6. Pendiente

- Envío de correo para invitaciones (hoy el enlace se comparte a mano).
- Consola de plataforma más allá del admin de Django: métricas globales e impersonación auditada (Fase 10).
- Cobro, renovación y bloqueo por falta de pago.
- Gestión de sucursales en la UI (el límite `locations` ya existe).
- Los límites se validan "antes de crear". Dos altas simultáneas podrían exceder un límite en 1 unidad; se aceptó así por simplicidad y se puede endurecer con un bloqueo por empresa si hace falta.
