# Documento 11 — Fase 10: administración del SaaS

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-10-12 |
| **Depende de** | [03 — Fase 4](03-fase-4-acceso-auditoria-planes.md) (planes y entitlements) |

---

## 1. Qué es

La **consola de plataforma** (`/platform`) es para el equipo de GestorPro, no para los clientes. Desde ahí se administran las empresas, los planes y las suscripciones, y se da soporte. Está separada de la app de las empresas: tiene su propio menú y su propia marca ("GestorPro · Plataforma").

**Quién entra:** solo usuarios con `is_platform_admin`. El acceso se da o se quita a una cuenta **existente**:

```bash
python manage.py platform_admin persona@gestorpro.co           # dar acceso
python manage.py platform_admin persona@gestorpro.co --revoke  # quitarlo
```

Nunca se crean usuarios ni contraseñas automáticamente (condición 13).

---

## 2. Principio de privacidad

El personal de la plataforma **no tiene membresía en las empresas**, así que no ve sus clientes, ventas ni facturas.

- **Métricas globales:** son de **uso**, como cuántas empresas hay, cuántas usaron el sistema esta semana, cuántas personas tienen acceso y cuántas ventas se registraron. **Nunca muestran montos** de negocio de los clientes. El único monto de la consola es el ingreso estimado **de GestorPro**: la suma de los precios de los planes activos.
- **Detalle de una empresa:** muestra datos de cuenta (personas, roles, último ingreso), el uso del plan y la bitácora.
- **Ver datos de negocio:** para eso hace falta una **sesión de soporte** (§5).

---

## 3. Pantallas

| Pantalla | Contenido |
|---|---|
| **Resumen** | Empresas activas, en uso esta semana, nuevas en 30 días e ingreso mensual estimado. Gráfico de empresas nuevas por mes, suscripciones por estado y por plan, pruebas que terminan esta semana y empresas que requieren gestión (prueba vencida o pago pendiente) |
| **Empresas** | Búsqueda por nombre, NIT o email de cualquier usuario. Filtros por estado, suscripción y tipo de negocio. **Nueva empresa:** la crea con su plan y genera el enlace de invitación del dueño, que se muestra una sola vez |
| **Detalle de empresa** | Suscripción (cambiar plan, estado, fin de la prueba y "pagado hasta", con nota), uso del plan, módulos, personas con acceso, accesos de soporte y bitácora. Acciones: **Invitar propietario**, **Suspender o Reactivar** y **Ver como soporte** |
| **Planes** | Precio, funcionalidades y límites de cada plan, editables sin desplegar código. Se validan contra el catálogo del Core (`FEATURES`, `LIMITS`). No se puede desactivar un plan que tiene empresas |
| **Bitácora** | Todo lo que el equipo hizo, con quién, cuándo e IP. Inmutable |

---

## 4. Suscripciones: qué bloquea y qué no

| Situación | Efecto |
|---|---|
| Prueba vencida, pago pendiente o cancelada | **Aviso** para quien administra la empresa ("Escríbenos…"). **No se bloquea el trabajo** |
| Empresa **suspendida** (acción manual, con motivo obligatorio) | Nadie de la empresa puede entrar; cualquier sesión de soporte abierta se cierra. Los datos se conservan |

Aún no hay cobro automático. Bloquear a un cliente por una fecha mal cargada sería peor que cobrar tarde, así que el corte es **siempre una decisión humana y auditada**.

La edición local usa una licencia sin fechas (`set_plan --no-end`) y nunca ve estos avisos.

**Transparencia:** cada cambio de suscripción o de estado queda en la bitácora de plataforma **y en la auditoría de la empresa** ("GestorPro cambió tu suscripción: estado (pago de octubre)").

---

## 5. Sesión de soporte (impersonación auditada)

Sirve para ayudar a un cliente ("no veo las ventas de ayer") viendo su empresa como la ven ellos.

| Regla | Cómo se cumple |
|---|---|
| **Motivo obligatorio** | Mínimo 10 caracteres. La empresa lo ve |
| **Solo lectura** | Rol virtual "Soporte GestorPro" con solo permisos `*.view`. **Además**, la autenticación rechaza todo método que no sea GET, HEAD u OPTIONS (403), aunque una vista no use permisos por rol: cambiar contraseña, cambiar de empresa, crear clientes… La única excepción es cerrar la propia sesión de soporte |
| **Con vencimiento** | 30 minutos. El token no tiene refresh |
| **Revocable al instante** | El token se valida **contra la base de datos en cada petición**. Cerrar la sesión, suspender la empresa o quitarle el acceso al agente lo invalida de inmediato |
| **Auditado y visible** | Inicio y fin en la **auditoría de la empresa** (la ve el dueño) y en la bitácora de plataforma. Se cuentan las consultas hechas |
| **Confinado** | El token lleva la empresa (`tid`) firmada; no ve datos de ninguna otra (test de aislamiento) |

**En pantalla:**
- una barra negra permanente: "Modo soporte · solo lectura · {empresa} · N min restantes · motivo", con **Salir del soporte**;
- los botones de crear, editar y borrar no aparecen, porque el rol no tiene esos permisos;
- al salir o al vencer, el agente vuelve a la consola con su propia sesión: sus tokens esperan en `sessionStorage` de esa pestaña.

**Implementación:**
- `core/access/support.py` y el modelo `SupportSession`: el Core debe poder validar el token.
- `platform/console/services.start_support`: la plataforma es quien lo crea.

---

## 6. API (`/api/platform/`, solo `is_platform_admin`)

| Endpoint | Método |
|---|---|
| `overview/` | GET |
| `tenants/` | GET (búsqueda, filtros, paginado) · POST (alta + enlace de invitación) |
| `tenants/<id>/` | GET |
| `tenants/<id>/status/` | POST `{status, reason}` |
| `tenants/<id>/subscription/` | PATCH `{plan?, status?, trial_ends_at?, current_period_end?, note?}` |
| `tenants/<id>/reinvite/` | POST `{email}` |
| `tenants/<id>/support/` | POST `{reason}` → token de soporte |
| `support/end/` | POST |
| `plans/` · `plans/<id>/` | GET · PATCH |
| `events/` | GET (`?tenant=`, `?action=`) |

El admin de Django (`/admin/`) sigue existiendo como herramienta interna.

---

## 7. Tests

- **`tests/platform/test_console.py`** (11 tests):
  - solo el personal de la plataforma entra;
  - las métricas no exponen montos y detectan la prueba vencida;
  - búsqueda por email del dueño;
  - alta con invitación;
  - cambios de suscripción en ambas auditorías;
  - suspender exige motivo y bloquea;
  - planes validados;
  - soporte de solo lectura, auditado y visible para la empresa;
  - el token de soporte muere al vencer o al revocar el acceso;
  - solo el personal abre soporte y no se entra a empresas suspendidas;
  - la bitácora es inmutable.
- **`tests/isolation/test_support_isolation.py`** (obligatorio en CI): el soporte en la empresa A no ve nada de la B, y el personal sin token de soporte no ve datos de ninguna empresa.

---

## 8. Pendiente

- **Cobro automático** con pasarela de pagos (Wompi, PayU…). `Subscription.external_ref` ya está reservado.
- **Segundo factor (2FA)** para el personal de la plataforma.
- **Precios de los planes:** decisión comercial pendiente; hoy figuran "por definir".
- **Avisos por correo** de pruebas que vencen.
