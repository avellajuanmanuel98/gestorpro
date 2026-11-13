# GestorPro → Plataforma SaaS + Miga (vertical panaderías)

## Documento 01 — Auditoría técnica, arquitectura objetivo y roadmap

| | |
|---|---|
| **Estado** | Borrador para aprobación — **no se ha modificado código de la aplicación** |
| **Fecha** | 2026-10-08 |
| **Alcance** | Fase 1 (auditoría) + propuesta de Fases 2–5 y roadmap de Fases 6–14 |
| **Base auditada** | `main` @ `65615b7` |

> **Cómo leer este documento.** Las secciones 1–8 describen lo que *existe hoy* (con evidencia: rutas de archivo y pruebas ejecutadas). Las secciones 9–15 describen lo que *proponemos construir*. La sección 16 lista riesgos y la 17 el roadmap. Al final hay una lista de **decisiones que necesito que apruebes** antes de empezar.

---

## Resumen ejecutivo

GestorPro es hoy un **mini-ERP monolítico Django + React** con buena intención arquitectónica (apps por dominio, JWT, TanStack Query, Decimal para dinero, un primer intento de multi-tenancy por `company_id`), pero **no está listo para ser un SaaS comercial**. Los hallazgos más importantes:

1. **El aislamiento entre empresas tiene fugas verificadas.** Un usuario de la Empresa A puede crear una factura que referencia un cliente y un producto de la Empresa B, y la API le devuelve el nombre del cliente ajeno (prueba ejecutada, ver §5.1). El filtrado por tenant es opt-in, vista por vista, y no cubre las relaciones.
2. **Producción borra la base de datos en cada deploy** (`Procfile` ejecuta `wipe_db`). Es correcto para una demo de portafolio, pero es incompatible con clientes reales. Ventaja colateral: **no hay datos productivos que migrar**, lo que abarata mucho la refactorización.
3. **El usuario demo es superusuario de Django** y sus credenciales son públicas en el README → acceso total a `/admin/` sobre todos los tenants.
4. **No existe el núcleo de un negocio de mostrador**: no hay POS, ni caja, ni movimientos de inventario, ni compras, ni gastos, ni auditoría. Facturar *no descuenta stock* (el README dice que sí).
5. **No hay tests** (los 5 `tests.py` están vacíos) ni CI.
6. **El frontend tiene dos generaciones visuales conviviendo**: 3 páginas rediseñadas (zinc + modo oscuro) y 7 páginas heredadas (gray, sin modo oscuro, sin el kit UI). Ninguna lista pagina: **solo se ven los primeros 20 registros**.

**Recomendación central:** no reescribir desde cero, pero tampoco "parchear". Conservar el stack (Django/DRF + React/TS/Tailwind/TanStack Query), conservar el kit UI y los patrones buenos, y **reconstruir la capa de dominio** sobre tres bases nuevas: *tenancy que falla cerrado*, *capa de servicios transaccional* e *inventario basado en libro de movimientos*. Sobre eso, Miga se construye como **composición de módulos + configuración de vertical**, no como fork.

---

## 1. Arquitectura actual de GestorPro

### 1.1 Vista general

```
                    ┌──────────────────────────────────────────┐
  Navegador ──────► │ Railway: gunicorn + Django 6              │
  (SPA React)       │  ├─ WhiteNoise sirve frontend/dist        │
                    │  ├─ /api/*  DRF + SimpleJWT               │
                    │  ├─ /admin/ Django admin                  │
                    │  └─ catch-all → index.html                │
                    └──────────────┬───────────────────────────┘
                                   │
                         PostgreSQL (Railway)       Groq API (LLM)
                         SQLite en desarrollo

  Además existen configs de deploy para Vercel (frontend/vercel.json)
  y Netlify (netlify.toml): 3 destinos de despliegue declarados.
```

Monolito modular: un único proyecto Django (`config/`) con apps en `apps/` y una SPA en `frontend/` que se compila a `frontend/dist` (versionado en git pese a estar en `.gitignore`) y la sirve el propio Django.

### 1.2 Backend

| Aspecto | Estado actual | Archivo |
|---|---|---|
| Framework | Django 6.0.4 + DRF 3.17 | `requirements.txt` |
| Apps | `companies, users, clients, billing, inventory, employees, suppliers, reports, assistant` | `config/settings.py` |
| Estilo de vistas | `generics.ListCreateAPIView` / `RetrieveUpdateDestroyAPIView` + `APIView` para métricas | `apps/*/views.py` |
| Lógica de negocio | En serializers (`InvoiceSerializer.create/update`) y en `Model.save()` (`InvoiceItem.save` recalcula la factura) | `apps/billing/` |
| Capa de servicios | **No existe** | — |
| Transacciones | **Ninguna** (`atomic`, `select_for_update` no aparecen en el código) | — |
| Paginación | `PageNumberPagination`, 20 por página | `settings.py` |
| Filtros | `SearchFilter`/`OrderingFilter` + query params manuales | vistas |
| Documentación | drf-spectacular → `/api/docs/` | `config/urls.py` |
| Comandos | `seed_demo` (ferretería), `wipe_db` (DROP SCHEMA) | `apps/users/management/commands/` |
| IA | Groq `llama-3.3-70b` vía SSE, con contexto armado desde la BD | `apps/assistant/views.py` |
| Tests | 5 archivos vacíos | `apps/*/tests.py` |

### 1.3 Base de datos y modelos

```
Company (tenant) ─┬─< User (role: admin|employee, company FK nullable)
                  ├─< Client         (document_number y email ÚNICOS GLOBALES)
                  ├─< Category       (unique: company+name)
                  ├─< Product        (code ÚNICO GLOBAL, stock: Integer)
                  ├─< Invoice ─< InvoiceItem >─ Product
                  │     (unique: company+number; company y client nullable)
                  ├─< Employee       (unique: company+document_number)
                  └─< Supplier
```

- **Dinero:** `DecimalField(12|14, 2)` — correcto. Pero los endpoints de métricas convierten a `float` antes de responder (`reports/views.py`, `billing/views.py`).
- **Stock:** un entero mutable en `Product.stock`. No hay historial, ni costo, ni unidad de medida, ni movimientos.
- **Migraciones:** desincronizadas respecto a los modelos. `makemigrations --check` genera cambios pendientes en `clients` e `inventory` (los modelos dicen `company` NOT NULL, las migraciones lo crean `null=True`). Las migraciones de `billing` se llaman `0002_initial`, `0003_initial` — síntoma de historial reescrito, compensado con `wipe_db` en cada deploy.

### 1.4 Autenticación

- SimpleJWT: access 8 h, refresh 7 días, rotación activada.
- `BLACKLIST_AFTER_ROTATION=True` pero la app `token_blacklist` **no está instalada** → la lista negra no funciona; no existe endpoint de logout en backend; un refresh robado es válido 7 días.
- Tokens en `localStorage` (expuestos ante cualquier XSS).
- Login por email; registro público crea Empresa + usuario `admin` (sin transacción: si falla la creación del usuario queda una empresa huérfana).
- Sin rate limiting en login, sin recuperación de contraseña, sin verificación de email.

### 1.5 Autorización

- Global: `IsAuthenticated`.
- Roles: `admin` y `employee`. **El rol solo se usa en un lugar**: editar la empresa (`companies/views.py`). Un `employee` puede crear, editar y borrar clientes, productos, facturas, empleados (con salarios) y proveedores.
- No hay modelo de permisos, ni roles por empresa, ni concepto de Super Admin de plataforma (solo `is_superuser` de Django).

### 1.6 APIs

REST plano, rutas por app bajo `/api/<app>/`. Endpoints de dashboard dispersos (`billing/summary`, `billing/monthly-revenue`, `billing/recent`, `reports/*`). Respuestas mezclan nombres en español (`mes`, `categoria`, `valor_inventario`) e inglés. Sin versionado (`/api/v1`).

### 1.7 Frontend

| Aspecto | Estado actual |
|---|---|
| Stack | React 19, TS, Vite 8, Tailwind 4, TanStack Query 5, Zustand 5, RHF + Zod 4, Recharts 3, lucide |
| Estructura | Por tipo técnico: `api/`, `components/{ui,<módulo>}`, `pages/<módulo>`, `store/`, `types/` |
| Estado servidor | TanStack Query (bien elegido), `staleTime` 5 min |
| Estado global | Zustand: `authStore` (usuario persistido en localStorage), `themeStore` |
| Rutas | `App.tsx` plano; `PrivateRoute` solo verifica un booleano persistido |
| HTTP | Axios con interceptor de refresh. El asistente usa `fetch` con **otra** convención de `VITE_API_URL` (en `client.ts` la variable incluye `/api`; en `assistant.ts` se le concatena `/api`) |
| Kit UI | `Button, Input, Modal, Badge, Skeleton, EmptyState` — bien hechos, poco adoptados |
| Tipos | `types/index.ts` manual (no generado desde OpenAPI) |

### 1.8 Configuración y despliegue

- `python-decouple` + `.env`. Seguridad HTTP de producción incompleta (sin `SECURE_SSL_REDIRECT`, HSTS, `SESSION_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`).
- `CSRF_COOKIE_SAMESITE='None'` con JWT en header: incoherente pero inocuo hoy.
- Versión de Python inconsistente: README 3.14, `runtime.txt` 3.13, `.pyc` de 3.14 versionados.
- `requirements.txt` incluye `anthropic` (sin uso) y `groq`.

---

## 2. Tecnologías — evaluación

| Tecnología | ¿Mantener? | Comentario |
|---|---|---|
| Django + DRF | **Sí** | Maduro, ORM con transacciones y `select_for_update`, admin útil para soporte interno. Ideal para un SaaS transaccional. |
| PostgreSQL | **Sí (único motor)** | Dejar SQLite. Necesitamos RLS, `NUMERIC`, índices parciales y paridad dev/prod (Docker Compose). |
| SimpleJWT | **Sí, reconfigurado** | Access corto, refresh en cookie httpOnly, blacklist, claim de tenant. |
| drf-spectacular | **Sí** | Y generar los tipos TS desde el esquema OpenAPI. |
| React + TS + Vite | **Sí** | |
| Tailwind 4 | **Sí** | Con tokens semánticos propios (hoy usa colores crudos). |
| TanStack Query | **Sí** | Bien usado; añadir convenciones de query keys y manejo global de errores. |
| Zustand | **Sí, acotado** | Sesión, tenant activo, carrito POS. |
| RHF + Zod | **Sí** | |
| Recharts | **Sí** | Suficiente; envolver en componentes de gráfico del sistema de diseño. |
| Groq/LLM | **Opcional** | Mover a módulo opcional, detrás de feature flag por plan. |
| Nuevas | — | Celery/RQ + Redis (tareas: reportes, emails, cierres), `django-filter`, pytest + factory_boy, Vitest + Testing Library, Playwright (E2E), Sentry, GitHub Actions. |

---

## 3. Fortalezas

1. **Separación por dominio** en apps Django: el límite mental existe, aunque no se respete del todo.
2. **Decimal para dinero** en modelos, con comentario explícito del porqué.
3. **Snapshot de precio** en `InvoiceItem.unit_price` (precio al momento de facturar) — idea correcta que reutilizaremos en ventas.
4. **`CompanyFilterMixin`**: primer paso real hacia multi-tenancy; `perform_create` asigna tenant y autor sin confiar en el cliente.
5. **Serializers de lista vs detalle** para aligerar respuestas.
6. **Kit UI base de buena calidad** (`Button` con variantes/tamaños/loading, `Modal` con `aria-modal`, `Skeleton`, `EmptyState`) y un layout con sidebar agrupado, drawer móvil y modo oscuro.
7. **Elección de librerías frontend** moderna y coherente.
8. **Localización** de partida correcta: `es-co`, `America/Bogota`, COP, IVA 19 %, tipos de documento colombianos.
9. **Asistente IA** con streaming: diferenciador vendible si se ancla a datos fiables.

## 4. Debilidades

| # | Debilidad | Impacto |
|---|---|---|
| D1 | Tenancy opt-in por vista, sin validar relaciones | Fuga de datos entre empresas (verificada) |
| D2 | Sin capa de servicios ni transacciones | Datos inconsistentes ante fallos/concurrencia |
| D3 | Inventario = entero mutable | Imposible auditar, costear, producir o registrar mermas |
| D4 | Roles binarios sin permisos | No soporta cajero / inventario / supervisor |
| D5 | Usuario ↔ 1 empresa (FK) | Un dueño con 2 panaderías o un contador externo no caben |
| D6 | Sin auditoría | Requisito explícito del producto |
| D7 | Sin planes reales (`Company.plan` es un enum) | No se pueden aplicar límites sin hardcodear |
| D8 | Sin tests ni CI | Cada refactor es a ciegas |
| D9 | Frontend con dos sistemas visuales | Producto se percibe "a medio terminar" |
| D10 | Listas sin paginación en UI | Pérdida silenciosa de datos a partir del registro 21 |
| D11 | Métricas engañosas en el dashboard | Pérdida de confianza del cliente (ver §15.1) |

## 5. Deuda técnica (priorizada)

### 5.1 Crítica — seguridad y pérdida de datos

| ID | Hallazgo | Evidencia |
|---|---|---|
| **S1** | **Referencias cruzadas entre tenants.** `InvoiceSerializer` acepta cualquier `client` y `product` por ID sin verificar que pertenezcan a la empresa. Lo mismo ocurre con `Product.category`. | Prueba ejecutada: usuario de empresa A hace `POST /api/billing/invoices/` con cliente y producto de empresa B → **201**, respuesta incluye `client_name: "Secreto B"`. |
| **S2** | **Unicidad global filtra existencia de datos ajenos.** `Client.email`, `Client.document_number` y `Product.code` son `unique=True` globales. | Prueba: empresa A crea cliente con el email de un cliente de B → **400 "Ya existe un Cliente con este email"**. Además bloquea a dos panaderías que comparten un proveedor/cliente o el código "PAN-001". |
| **S3** | **`wipe_db` en cada deploy** de producción. | `Procfile` |
| **S4** | **Usuario demo superusuario con credenciales públicas** → `/admin/` con acceso global. | `seed_demo.py` usa `create_superuser`; README publica la contraseña. |
| **S5** | Sin control de permisos por rol (cualquier empleado borra facturas y ve salarios). | `apps/*/views.py` |
| **S6** | Refresh tokens no revocables, tokens en `localStorage`, sin rate limiting de login. | `settings.py`, `api/client.ts` |
| **S7** | El asistente devuelve `str(e)` de excepciones internas al cliente. | `assistant/views.py` |

Lo que **sí** funciona: acceso directo por ID a un objeto ajeno devuelve 404 (probado con `DELETE /api/clients/{id}`), y un `employee` no puede editar la empresa (403).

### 5.2 Alta — integridad del negocio

- Facturar no mueve inventario; no hay `atomic()`; `InvoiceItem.save()` recalcula la factura completa por cada línea (N escrituras) y `update()` borra y recrea líneas.
- `unit_price` y `tax_rate` vienen del cliente: un usuario puede vender a $1.
- Número de factura digitado a mano (sin secuencia; colisiones y huecos).
- `valor_inventario` en `reports/views.py` suma `price` (no `price × stock`, ni costo) → **la cifra es incorrecta**.
- `LowStockView` y vistas de reporte no usan el mixin: si `user.company` es `None` filtran por `company IS NULL`.
- Migraciones desincronizadas; `company` nullable en `Invoice`.
- `CompanyFilterMixin.perform_create` contiene código muerto (`inspect.signature` sin uso).

### 5.3 Media — mantenibilidad

- Lógica de dominio en serializers y `Model.save()`.
- `formatCurrency` reimplementado 5 veces con comportamientos distintos (compacto vs. completo).
- Labels de estado duplicados en backend (3 sitios) y frontend.
- Tipos TS escritos a mano → divergencia silenciosa con la API.
- Páginas de 300–435 líneas mezclando fetch, estado, tabla y modal (`InventoryPage`, `DashboardPage`, `AssistantPanel`, `ReportsPage`).
- `frontend/dist` y `__pycache__` versionados.
- Tres destinos de deploy (Railway, Vercel, Netlify).

### 5.4 Baja

- `App.css` es el CSS de la plantilla de Vite sin usar.
- Docstring del asistente menciona Anthropic pero usa Groq; dependencia `anthropic` sin uso.
- `Modal` registra el listener de `Escape` aunque esté cerrado; sin focus trap.

---

## 6. Componentes a REUTILIZAR

Se reutilizan tal cual o con ajustes cosméticos, y pasan a formar parte del Core.

| Componente | Destino | Motivo |
|---|---|---|
| Stack completo (Django/DRF, React/TS/Vite/Tailwind/TanStack/Zustand/RHF/Zod/Recharts) | Core | Adecuado para el producto; cambiarlo no aporta valor al cliente. |
| `users.User` (email como login, `UserManager`) | `core.identity` | Base correcta. Se le **quitan** `company` y `role` (pasan a `Membership`). |
| Patrón serializer lista/detalle | Convención Core | Rendimiento en listados. |
| Patrón snapshot de precio en líneas | Ventas, compras, producción | Integridad histórica. |
| drf-spectacular | Core | Base para generar el cliente TS. |
| Kit UI: `Button`, `Input`, `Badge`, `Skeleton`, `EmptyState` | `shared/ui` | Buena API de props; se re-tematizan con tokens. |
| `AppLayout` (estructura sidebar agrupado + drawer + header) | `app/layout` | El esqueleto es correcto; la navegación pasa a generarse desde un registro de módulos. |
| Interceptor Axios de refresh | `shared/api` | Se adapta a refresh por cookie y a cola de peticiones concurrentes. |
| `themeStore` + script anti-flash | `shared/theme` | Funciona. |
| Configuración de localización (`es-co`, `America/Bogota`) | Core (por tenant) | Pasa a ser configurable por tenant. |

## 7. Componentes a REFACTORIZAR

Funcionan, pero hay que cambiarlos para soportar multi-tenancy real, permisos y verticales.

| Componente | Cambios | Motivo |
|---|---|---|
| `companies.Company` | → `Tenant` (o se conserva el nombre `Company` como entidad tenant — ver decisión D-2). Se añaden `vertical`, `timezone`, `currency`, `status`; `plan` sale a `Subscription`. | Es el tenant, pero mezcla datos fiscales, plan y estado. |
| `CompanyFilterMixin` | → `TenantScopedViewMixin` + manager que **falla cerrado** + campos FK tenant-aware. | Hoy es opt-in y no protege relaciones (S1). |
| `clients.Client` → `Customer` | Unicidad por tenant; documento/email opcionales (en panadería la mayoría de ventas son a "Consumidor final"). | S2 + realidad del negocio. |
| `suppliers.Supplier` | Categoría como catálogo por tenant (no enum fijo), unicidad por tenant. | Las categorías de una panadería ("Harinas", "Lácteos") no son las de una ferretería. |
| `inventory.Category` | Jerarquía opcional, tipo (productos/ingredientes/gastos). | Reutilizable por todos los verticales. |
| `billing.Invoice` | Se mantiene como **documento de cuentas por cobrar** (facturas a crédito, cotizaciones B2B, pedidos de tortas). Lógica a servicio transaccional, numeración por secuencia, precios resueltos en servidor, integración con inventario. | Sigue siendo útil (panadería que vende a cafeterías/oficinas), pero **no es el POS**. |
| `reports` | Se reconstruye su lógica (ver §8), pero la idea de endpoints de agregación se conserva, con parámetro de período y comparación. | Hoy: período fijo, floats, cifra de inventario errónea. |
| `assistant` | Módulo opcional; contexto armado desde servicios de reporting del vertical; errores sanitizados; límite por plan; registro en auditoría. | Valor diferencial, pero hoy describe un negocio de facturas, no una panadería. |
| `employees` | Módulo opcional "Personal" (no MVP de Miga); salario solo visible con permiso. | Datos sensibles; no es core de un POS. |
| Páginas heredadas (Invoices, Inventory, Reports, Suppliers, Employees, Company, Register) y todos los `*Form.tsx` | Migrar al sistema de diseño, `DataTable` compartido, paginación, toasts, confirmaciones accesibles, modo oscuro. | D9, D10. |
| `Modal` | Focus trap, retorno de foco, variante `Drawer`/`Sheet` lateral para formularios largos. | Accesibilidad y ergonomía. |
| Settings/despliegue | Settings por entorno (`base/dev/prod/test`), headers de seguridad, un solo destino de deploy, build del frontend en CI. | S3, §1.8. |

## 8. Componentes a RECONSTRUIR

Más barato y seguro rehacer que adaptar.

| Componente | Motivo |
|---|---|
| **Modelo de inventario** (`Product.stock` entero) | No admite unidades (g, kg, ml), decimales, costo, historial ni ubicaciones. Recetas, producción, mermas y rentabilidad dependen de un **libro de movimientos**. Adaptar el entero sería apilar parches. |
| **Modelo de roles/permisos** | `role` en `User` es estructuralmente incorrecto para multi-empresa y no escala a roles personalizados. |
| **Flujo de creación de facturas** | Lógica en `save()` + serializer, sin transacción, precios del cliente. Se rehace como servicio. |
| **Migraciones** | Historial reescrito y desincronizado. Como producción se borra en cada deploy, **se puede regenerar un historial limpio una única vez** (requiere tu aprobación, D-1) y a partir de ahí no se reescribe nunca más. |
| **Dashboard** | Métricas genéricas de facturación con datos falsos (tendencia "+12 %" hardcodeada, badge "En tiempo real" con caché de 5 min, "Clientes activos" que cuenta todos). Se diseña de nuevo alrededor de decisiones de una panadería. |
| **`seed_demo`** | Es una ferretería. Se reemplaza por seeds por vertical (panadería colombiana) sin superusuario. |
| **`wipe_db`** | Se elimina del arranque de producción. Queda solo como comando de desarrollo protegido por `DEBUG`. |

## 9. Funcionalidades NUEVAS

**Core:** membresías multi-empresa, roles y permisos granulares, sucursales (`Location`), unidades de medida, libro de inventario, compras/recepción de mercancía, gastos, POS, caja (sesiones, arqueo, movimientos), devoluciones/anulaciones, secuencias de numeración, auditoría, configuración por tenant, recuperación de contraseña, invitación de usuarios.

**Módulos de capacidad (compartidos entre verticales):** recetas, producción, mermas con motivos, pedidos por encargo (fase posterior).

**Vertical Miga:** paquete de configuración de panadería, dashboard de panadería, reportes de rentabilidad y producción, datos demo colombianos, terminología.

**Platform:** panel Super Admin, planes, límites, funcionalidades por plan, suscripciones, métricas globales, impersonación auditada (soporte).

**Ingeniería:** tests, CI/CD, observabilidad (Sentry + logs estructurados), backups.

---

## 10. Propuesta de Core

### 10.1 Criterio de pertenencia

Un módulo es **Core** si (a) lo necesita *cualquier* PYME de mostrador y (b) no contiene vocabulario de un vertical. Si lo necesitan *varios* verticales pero no todos, es un **módulo de capacidad**. Si solo tiene sentido para un tipo de negocio, es **vertical**.

| Módulo | Ubicación | Justificación |
|---|---|---|
| Autenticación, usuarios, membresías | **Core** | Universal. |
| Tenants / empresas, sucursales | **Core** | Universal; sucursales desde el día 1 (panaderías con 2–3 puntos son comunes, y retrofitarlas después es carísimo). |
| Roles y permisos | **Core** | Catálogo de permisos lo aporta cada módulo. |
| Catálogo de ítems, categorías, unidades | **Core** | Un `Item` sirve como producto, ingrediente o servicio. |
| Clientes, proveedores | **Core** | Universal. |
| Inventario (libro de movimientos, existencias, costo promedio) | **Core** | Toda PYME con stock. |
| **Mermas** | **Core (tipo de movimiento) + UI en módulo de capacidad** | Toda tienda tiene pérdidas; la panadería las registra a diario y necesita motivos y reportes específicos. |
| Ventas / POS, devoluciones | **Core** | Universal. |
| Caja | **Core** | Universal en comercio de mostrador. |
| Compras, gastos | **Core** | Universal. |
| Facturación a crédito / cotizaciones (actual `billing`) | **Core (opcional)** | B2B; algunos negocios no lo usan. |
| Reportes base (ventas, caja, inventario, gastos) | **Core** | Universal; los verticales añaden reportes. |
| Auditoría, configuración | **Core** | Universal. |
| **Recetas** | **Capacidad** | Panaderías, pastelerías, restaurantes, cafeterías. No ferreterías. |
| **Producción por lotes** | **Capacidad** | Panaderías, pastelerías, cocinas centrales. |
| Descarga por receta al vender (capuchino) | **Capacidad** | Cafeterías, restaurantes, panaderías con barra. |
| Pedidos por encargo (tortas) | **Capacidad** (fase posterior) | Pastelerías, panaderías, restaurantes con catering. |
| Mesas/comandas | Capacidad futura (Restaurantes) | Fuera de Miga. |
| Empleados/RR. HH. | Módulo opcional | No es necesario para el MVP de Miga. |
| Asistente IA | Módulo opcional (por plan) | Diferenciador, no imprescindible. |

### 10.2 Principios de diseño del Core

1. **Tenancy que falla cerrado**: sin contexto de tenant, una consulta a un modelo tenant lanza error en lugar de devolver todo.
2. **Capa de servicios**: toda operación que toca más de un agregado (venta → caja → inventario → auditoría) vive en una función de servicio con `transaction.atomic()`. Vistas y serializers no contienen reglas de negocio.
3. **El servidor es la fuente de verdad del dinero**: precios, impuestos, descuentos y totales se calculan en backend. El frontend envía intención (ítem, cantidad, descuento solicitado), nunca importes.
4. **Libros inmutables**: movimientos de inventario, movimientos de caja y auditoría son *append-only*. Las correcciones son movimientos compensatorios, no ediciones.
5. **Snapshots**: precio, costo, impuestos y receta se copian en el documento en el momento del hecho.
6. **Extensión por registro, no por `if vertical == 'bakery'`**: los módulos se registran (permisos, rutas, navegación, widgets de dashboard, reportes, seeds) y el tenant habilita los que su plan y vertical permiten.

---

## 11. Arquitectura multi-tenant propuesta

### 11.1 Estrategias evaluadas

| Estrategia | Aislamiento | Coste operativo | Analítica de plataforma | Encaje con GestorPro |
|---|---|---|---|---|
| BD por tenant | Máximo | Muy alto (N bases, N migraciones, N backups) | Muy difícil | ✗ Desproporcionado para PYMES |
| Schema por tenant (`django-tenants`) | Alto | Alto: migraciones × N schemas, pooling complicado, tests más lentos | Difícil (consultas cross-schema) | ✗ Reescribe el routing; miles de schemas pequeños degradan Postgres |
| **Schema compartido + `tenant_id` + defensa en profundidad** | Alto *si se aplica en varias capas* | Bajo | Trivial | ✓ **Recomendada.** Es la evolución natural del código actual |

Una panadería genera del orden de cientos de tickets diarios: el volumen por tenant es pequeño y el número de tenants potencialmente grande. Ese es exactamente el perfil para el que el modelo de tabla compartida es el estándar de la industria. El riesgo de ese modelo es el error humano (olvidar un filtro), por eso la propuesta no es "una columna", sino **cinco capas**:

### 11.2 Las cinco capas de aislamiento

```
 Petición HTTP
   │
   ▼
 [1] Autenticación ── JWT con claim `tid` (tenant activo) + verificación
   │                  de Membership activa en BD en cada request
   ▼
 [2] Contexto ─────── middleware fija tenant en un ContextVar
   │                  (y en Postgres: SET LOCAL app.tenant_id)
   ▼
 [3] ORM ──────────── TenantModel con manager por defecto que filtra por el
   │                  ContextVar y LANZA ERROR si no hay contexto.
   │                  Acceso global solo vía `.unscoped()` explícito y auditado
   ▼
 [4] Validación ───── TenantPrimaryKeyRelatedField en serializers:
   │                  toda FK entrante se resuelve dentro del tenant (cierra S1)
   ▼
 [5] Base de datos ── Constraints compuestas (tenant_id, code) y
                      Row-Level Security de PostgreSQL como red final
                      (fase de seguridad; las capas 1–4 van desde el inicio)
```

Más un **test automático de aislamiento** que recorre todos los endpoints registrados con dos tenants y verifica que ninguno devuelve, acepta ni referencia datos ajenos. Este test se ejecuta en CI y bloquea el merge.

### 11.3 Usuarios, membresías y tenant activo

```
User (identidad global: email, password)
  └─< Membership (user, tenant, role, status, default_location)
         └─ Role (por tenant) ─< RolePermission >─ Permission (catálogo en código)
```

- Un usuario puede pertenecer a varias empresas (dueño con dos negocios, contador externo). Selector de empresa en el header.
- Cambiar de empresa emite un nuevo access token con otro `tid`.
- Los **Super Admin** son `User.is_platform_admin=True`, **no tienen membresía**, usan una API separada (`/api/platform/`) y un área de UI separada. No pueden operar dentro de un tenant salvo mediante **impersonación explícita, temporal y auditada**.

### 11.4 Unicidad y numeración

- Toda restricción única de negocio incluye `tenant_id`: `(tenant, sku)`, `(tenant, document_type, document_number)`.
- Numeración de documentos con tabla `Sequence(tenant, location, doc_type, prefix, next_value)` bloqueada con `select_for_update` dentro de la transacción del documento: sin colisiones ni huecos por concurrencia.

---

## 12. Separación Core / Capabilities / Verticals / Platform

### 12.1 Capas

```
┌────────────────────────────────────────────────────────────────────┐
│ PLATFORM   (solo GestorPro como empresa)                           │
│   tenants admin · planes · suscripciones · límites · métricas       │
│   globales · impersonación · feature flags                          │
├────────────────────────────────────────────────────────────────────┤
│ VERTICALS  (paquetes: configuración + UX + pocas features propias) │
│   bakery (Miga): preset de módulos, categorías, motivos de merma,  │
│   unidades, dashboard, reportes, terminología, seeds, onboarding   │
│   [futuro] restaurant · cafe · retail                              │
├────────────────────────────────────────────────────────────────────┤
│ CAPABILITIES (módulos opcionales reutilizables)                    │
│   recipes · production · waste-ui · made-to-order · ai-assistant   │
│   · hr                                                             │
├────────────────────────────────────────────────────────────────────┤
│ CORE                                                               │
│   tenancy · identity · access(roles/permisos) · audit · settings   │
│   catalog(items/categorías/unidades) · customers · suppliers       │
│   inventory(ledger) · sales(POS) · cash · purchasing · expenses    │
│   receivables(billing) · reporting-base · notifications            │
├────────────────────────────────────────────────────────────────────┤
│ SHARED KERNEL: money · base models · service base · errors ·       │
│   pagination · sequences · time/periods                            │
└────────────────────────────────────────────────────────────────────┘
```

**Reglas de dependencia (verificadas en CI con `import-linter`):**
- Core no importa de Capabilities, Verticals ni Platform.
- Capabilities importan de Core; no entre sí salvo declaración explícita (production → recipes).
- Verticals importan de Core y Capabilities; nunca al revés.
- Platform lee de Core (tenants, usuarios) pero Core no conoce Platform: la consulta de entitlements se hace a través de una interfaz (`entitlements.has_feature(tenant, "production")`).

**Qué es un vertical (y qué no):** Miga **no** contiene modelos `PanaderiaProduct`. Contiene un `VerticalDefinition` que declara módulos habilitados, valores por defecto (categorías, motivos de merma, métodos de pago, unidades), widgets y layout del dashboard, reportes adicionales, textos y onboarding. Las pocas funcionalidades realmente exclusivas (p. ej. *producción sugerida según ventas del mismo día de la semana*) viven en `verticals/bakery`.

### 12.2 Estructura de carpetas propuesta

```
backend/
  config/settings/{base,dev,prod,test}.py
  gestorpro/
    kernel/            money.py, models.py (TenantModel, TimeStamped), services.py,
                       sequences.py, periods.py, exceptions.py
    core/
      tenancy/  identity/  access/  audit/  settings/
      catalog/  customers/  suppliers/  inventory/
      sales/    cash/       purchasing/ expenses/  receivables/
      reporting/
    capabilities/
      recipes/  production/  waste/  ai_assistant/  hr/
    verticals/
      bakery/   (definition.py, seeds/, reports/, dashboard.py)
    platform/
      tenants_admin/  billing_plans/  subscriptions/  metrics/
  tests/

frontend/src/
  app/          router, providers, guards, módulo-registry, layout
  shared/       ui/ (design system), charts/, lib/(money, dates, periods), api/(cliente generado)
  core/         auth/ customers/ suppliers/ catalog/ inventory/ pos/ cash/
                purchasing/ expenses/ reports/ settings/ users/
  capabilities/ recipes/ production/ waste/ assistant/
  verticals/    bakery/ (dashboard, reports, onboarding, copy)
  platform/     (área Super Admin; chunk separado)
```

Cada módulo frontend exporta un manifiesto: `{ id, routes, navItems, permissions, requiredFeature, dashboardWidgets }`. El sidebar y el router se construyen filtrando el registro por **permisos del usuario ∧ funcionalidades del plan ∧ módulos del vertical**. El frontend oculta lo que no se puede usar (UX); **el backend es quien bloquea** (seguridad).

---

## 13. Modelo de datos propuesto

> Convenciones: todas las entidades tenant heredan `TenantModel(tenant FK, created_at, updated_at, created_by)`. Dinero: `NUMERIC(14,2)` (COP no usa centavos en la práctica, pero se conservan 2 decimales para cálculos de costo unitario e impuestos; se redondea con `ROUND_HALF_UP` en un único helper `Money`). Cantidades: `NUMERIC(14,4)` (gramos de harina, fracciones de unidad). IDs: `BigAutoField` interno + `public_id` UUID para URLs y API (evita enumeración).

### 13.1 Platform

```
Plan(code, name, price_monthly, is_public, sort)
PlanFeature(plan, feature_key)                        -- "production", "multi_location", "ai"
PlanLimit(plan, limit_key, value)                     -- "users"=3, "locations"=1, "items"=500
Subscription(tenant, plan, status[trialing|active|past_due|canceled|suspended],
             started_at, current_period_start, current_period_end, trial_ends_at,
             cancel_at, external_ref)
SubscriptionEvent(subscription, type, payload, at)    -- historial
```
Los límites y features **no están en código**: el código pregunta por una clave; el valor viene de la BD. Planes iniciales: STARTER / BUSINESS / PRO (contenido a definir contigo).

### 13.2 Core — Identidad, tenancy y acceso

```
Tenant(name, legal_name, nit, slug, vertical, status, timezone, currency, locale,
       logo, address, phone, email, created_at)
Location(tenant, name, address, is_default, is_active)          -- sucursal
User(email, first_name, last_name, password, is_platform_admin, last_login)
Membership(user, tenant, role, status[invited|active|suspended], default_location)
Permission(code, module, description)                           -- sembrado desde código
Role(tenant, code, name, is_system)                             -- OWNER, ADMIN, CASHIER,
RolePermission(role, permission)                                --  INVENTORY, SUPERVISOR
AuditLog(tenant, actor, action, entity_type, entity_id, summary, changes JSONB,
         ip, user_agent, impersonated_by, at)                   -- append-only
TenantSetting(tenant, key, value JSONB)
Sequence(tenant, location, doc_type, prefix, next_value)
```

### 13.3 Core — Catálogo e inventario

```
UnitOfMeasure(code, name, dimension[mass|volume|count], factor_to_base)   -- global: g, kg, ml, l, und, docena
Category(tenant, name, kind[sellable|ingredient|expense], parent, sort)
Item(tenant, public_id, sku, name, category, kind[finished_good|raw_material|resale|service],
     base_unit, is_sellable, is_purchasable, track_stock,
     sale_price, tax_rate, cost_method[avg], avg_cost, min_stock,
     image, is_active)
ItemPrice(item, location?, price, valid_from)          -- historial de precios (auditable)

StockLevel(tenant, item, location, quantity, avg_cost, updated_at)   -- materializado
StockMovement(tenant, item, location, type, quantity(+/-), unit, quantity_base,
              unit_cost, total_cost, source_type, source_id, reason, user, at)
   type ∈ {purchase_receipt, sale, sale_return, production_consume, production_output,
           waste, adjustment_in, adjustment_out, transfer_in, transfer_out, opening}
```

**Separación materia prima / producto terminado:** es un único `Item` con `kind`, y la UI los presenta en pantallas distintas (*Productos* e *Ingredientes*). Motivo: compras, existencias, unidades, costo, mermas y alertas aplican igual a ambos; dos tablas duplicarían toda esa lógica. Hay ítems que son ambas cosas a la vez en la práctica (la *masa madre* producida y consumida; el *queso* que se usa en buñuelos y también se vende por libra).

**Costeo:** costo promedio ponderado móvil, recalculado en cada entrada (compra, producción). Cada salida registra el costo vigente → el costo de ventas y el de mermas quedan congelados y los reportes no cambian retroactivamente.

**Concurrencia:** cada servicio que mueve stock bloquea las filas `StockLevel` afectadas (`select_for_update`, ordenadas por id para evitar deadlocks), inserta movimientos y actualiza el nivel en la misma transacción. Política de stock negativo configurable por tenant (en panadería se suele permitir vender aunque no se haya registrado aún la producción; se reporta como alerta).

### 13.4 Core — Ventas, caja, compras y gastos

```
Customer(tenant, doc_type, doc_number, name, email, phone, ...)  -- "Consumidor final" por defecto
Supplier(tenant, nit, name, contact, category, ...)

Sale(tenant, location, number, cash_session, customer, cashier, status[completed|voided],
     subtotal, discount_total, tax_total, total, cost_total, completed_at,
     voided_at, voided_by, void_reason)
SaleLine(sale, item, quantity, unit_price, discount, tax_rate, tax_amount,
         line_total, unit_cost)                                 -- snapshots
Payment(sale, method, amount, tendered, change, reference)
PaymentMethod(tenant, code, name, kind[cash|card|transfer|wallet], affects_cash_drawer, is_active)
                       -- Efectivo, Tarjeta, Nequi, Daviplata, Transferencia
SaleReturn(tenant, sale, number, reason, total, refund_method, restock, user, at)
SaleReturnLine(return, sale_line, quantity, amount)

CashRegister(tenant, location, name)
CashSession(register, opened_by, opened_at, opening_amount, closed_by, closed_at,
            expected_amount, counted_amount, difference, denominations JSONB,
            status[open|closed], notes)
CashMovement(session, type[sale|refund|income|expense|withdrawal|deposit],
             amount(+/-), method, reference_type, reference_id, reason, user, at)

PurchaseReceipt(tenant, location, supplier, number, invoice_ref, status, total, received_at)
PurchaseReceiptLine(receipt, item, quantity, unit, unit_cost, total)
ExpenseCategory(tenant, name)
Expense(tenant, location, category, supplier, amount, method, cash_session?, date, notes, attachment)

Invoice / InvoiceLine  (actual billing, refactorizado: cuentas por cobrar y cotizaciones)
```

Invariantes que garantiza el servicio `sales.complete_sale()` en **una sola transacción**:
`Σ payments = total` · existe sesión de caja abierta del cajero · se crea `CashMovement` por los pagos en efectivo · se crean `StockMovement` por cada línea con `track_stock` · `cost_total` = Σ costo vigente · `AuditLog`. Anular una venta (`void_sale`) genera los movimientos inversos; nunca borra.

**Arqueo:** `expected_amount = opening + Σ cash_movements` (solo métodos con `affects_cash_drawer`). Otros métodos se concilian aparte. La diferencia queda registrada y auditada; cerrar con diferencia mayor a un umbral exige permiso de supervisor.

### 13.5 Capabilities — Recetas, producción y mermas

```
Recipe(tenant, product(Item), version, is_active, yield_quantity, yield_unit,
       notes, created_by)
RecipeLine(recipe, ingredient(Item), quantity, unit, waste_pct, sort)
   costo_estimado(recipe) = Σ cantidad_base × avg_cost(ingrediente) × (1 + waste_pct)
   costo_unitario = costo_estimado / rendimiento

ProductionBatch(tenant, location, number, recipe, recipe_version, planned_qty,
                produced_qty, status[draft|completed|cancelled],
                total_cost, unit_cost, produced_by, produced_at, notes)
ProductionConsumption(batch, ingredient, planned_qty, actual_qty, unit_cost, total_cost)

WasteReason(tenant, code, name)       -- Vencido, Quemado, Dañado, No vendido, Prueba/degustación
WasteRecord(tenant, location, item, quantity, unit, reason, unit_cost, total_cost,
            user, at, notes)  →  StockMovement(type=waste)
```

- La receta tiene **versiones**: al cambiar ingredientes se crea una nueva; los lotes ya producidos conservan su costo real.
- Completar un lote (`production.complete_batch`) en una transacción: consume ingredientes (cantidades reales, que pueden diferir de las planeadas), genera el producto terminado con costo = Σ consumos, actualiza costo promedio del producto, audita.
- Escalado: producir 150 buñuelos con una receta de rendimiento 50 multiplica por 3 las cantidades propuestas; el usuario puede ajustar.
- **Descarga al vender** (capuchino, chocolate): ítems marcados `consume_on_sale` descuentan sus ingredientes en el momento de la venta usando la receta activa. Previsto para Fase 8.

### 13.6 Ejemplo de cálculo (el buñuelo del enunciado)

| Ingrediente | Cantidad | Costo promedio | Subtotal |
|---|---|---|---|
| Harina de maíz | 1.000 g | $4,20 / g | $4.200 |
| Queso costeño | 500 g | $22,00 / g | $11.000 |
| Huevo | 10 und | $600 / und | $6.000 |
| Aceite | 200 ml | $12,00 / ml | $2.400 |
| **Costo de producción** | | | **$23.600** |
| Rendimiento | 50 und | Costo unitario | **$472** |
| Precio de venta | | | $1.500 |
| **Margen unitario** | | | **$1.028 (68,5 %)** |

*(Valores ilustrativos; los datos demo usarán precios de referencia del mercado colombiano 2026.)*

---

## 14. Módulos de Miga

| Módulo | Para quién | Qué resuelve (en términos del negocio) |
|---|---|---|
| **Inicio (Dashboard)** | Dueño, admin | "¿Cómo voy hoy y qué tengo que hacer?" |
| **Vender (POS)** | Cajero | Vender en < 5 s por cliente: grilla por categoría, búsqueda, cantidades rápidas, pago mixto, cambio, ticket |
| **Caja** | Cajero, supervisor | Abrir, registrar ingresos/egresos/retiros, arquear y cerrar con diferencia explicada |
| **Ventas** | Admin, supervisor | Historial, detalle, anulación con motivo y permiso, devoluciones |
| **Productos** | Admin | Catálogo vendible: precio, costo (desde receta), margen, stock, mínimo |
| **Ingredientes** | Inventario | Materias primas, unidades, costo promedio, stock crítico |
| **Recetas** | Admin, producción | Composición, rendimiento, costo y margen en vivo al editar |
| **Producción** | Inventario/producción | Registrar lotes del día, consumo real, historial, costo producido |
| **Mermas** | Todos (con permiso) | Registro en 2 toques: producto, cantidad, motivo |
| **Inventario** | Inventario | Existencias, movimientos (kardex), ajustes, conteo físico |
| **Compras** | Inventario, admin | Recepción de mercancía de proveedores → stock y costo |
| **Gastos** | Admin | Arriendo, servicios, nómina, etc., por categoría |
| **Clientes / Proveedores** | Admin | Directorios |
| **Reportes** | Dueño, admin | Ventas, rentabilidad, inventario, producción, mermas, gastos, caja |
| **Configuración** | Owner, admin | Empresa, sucursales, usuarios y roles, métodos de pago, impuestos, motivos de merma |

### 14.1 Roles iniciales (permisos editables, roles adicionales permitidos según plan)

| Permiso (resumen) | OWNER | ADMIN | SUPERVISOR | CASHIER | INVENTORY |
|---|:-:|:-:|:-:|:-:|:-:|
| Vender, abrir/cerrar su caja | ✓ | ✓ | ✓ | ✓ | – |
| Aplicar descuento > umbral | ✓ | ✓ | ✓ | – | – |
| Anular venta / devolución | ✓ | ✓ | ✓ | – | – |
| Aprobar cierre con diferencia | ✓ | ✓ | ✓ | – | – |
| Registrar merma | ✓ | ✓ | ✓ | ✓ | ✓ |
| Producción, compras, ajustes de inventario | ✓ | ✓ | ✓ | – | ✓ |
| Ver costos y márgenes | ✓ | ✓ | ✓ | – | ✓ |
| Editar precios, recetas | ✓ | ✓ | – | – | – |
| Gastos | ✓ | ✓ | – | – | – |
| Reportes financieros | ✓ | ✓ | parcial | – | – |
| Usuarios, roles, configuración | ✓ | ✓ | – | – | – |
| Suscripción, eliminar empresa | ✓ | – | – | – | – |

### 14.2 Dashboard de Miga (accionable, no decorativo)

```
┌ Hoy ▾ (Hoy · Ayer · 7 días · 30 días · Este mes · Mes anterior · Este año · Personalizado)  vs período anterior ┐
│ VENTAS            UTILIDAD ESTIMADA     TICKET PROMEDIO     TRANSACCIONES                                    │
│ $1.850.000        $620.000              $18.500             102                                             │
│ ▲ 12,4 % vs mar.  ▲ 8,2 %               ▼ 1,1 %             ▲ 13,3 %                                        │
├──────────────────────────────────────────────────────────────┬──────────────────────────────────────────────┤
│ Ventas por hora (hoy vs mismo día semana pasada)             │ Requiere atención                             │
│  línea + área tenue del período anterior                     │  • 3 ingredientes bajo mínimo (Queso costeño) │
│                                                              │  • Merma de hoy 4,1 % (meta 3 %)              │
│                                                              │  • Caja 2 abierta desde hace 11 h             │
├──────────────────────────────┬───────────────────────────────┼──────────────────────────────────────────────┤
│ Más vendidos (unid. y $)     │ Más rentables (margen $)      │ Caja: esperado vs contado, movimientos        │
└──────────────────────────────┴───────────────────────────────┴──────────────────────────────────────────────┘
```

Cada KPI: valor, variación contra el período comparable (mismo día de la semana anterior para "Hoy", no "ayer", porque la panadería vende muy distinto un sábado que un lunes), tooltip con la definición, y clic para ir al reporte filtrado. El bloque **"Requiere atención"** es el corazón del producto: convierte datos en tareas.

Variaciones con datos insuficientes muestran "—" con explicación, **nunca un número inventado**.

### 14.3 Reportes (todos con período, comparación, sucursal y exportación CSV)

- **Ventas:** total, transacciones, ticket promedio, crecimiento, por hora / día de semana / método de pago / cajero / categoría.
- **Rentabilidad:** por producto: unidades, ingreso, costo, margen $ y %; matriz *volumen × margen* (estrellas, caballos de batalla, enigmas, perros) para decidir qué empujar y qué eliminar.
- **Inventario:** valor (a costo), bajo mínimo, agotados, rotación, días de cobertura de ingredientes críticos, kardex.
- **Producción:** producido por día y producto, costo producido, producido vs. vendido vs. merma (**tasa de desperdicio por producto**: el indicador clave de una panadería).
- **Mermas:** por motivo, producto, día, costo.
- **Gastos:** por categoría, mensual, evolución; **utilidad operativa estimada** = ventas − costo de ventas − mermas − gastos.
- **Caja:** sesiones, esperado vs. contado, diferencias por cajero, movimientos.

---

## 15. Sistema UX/UI

### 15.1 Diagnóstico UX/UI actual

| Área | Hallazgo |
|---|---|
| **Coherencia** | 3 de 10 páginas usan la paleta `zinc` + modo oscuro + kit UI; 7 páginas y todos los formularios usan `gray`, inputs nativos y no soportan modo oscuro. Al activar el modo oscuro, la mayor parte de la app se rompe visualmente. |
| **Identidad** | Degradado índigo→violeta en logo, avatar, barras y texto; "glow" de colores en tarjetas, clase `glass`, halos difuminados detrás de iconos, tarjetas que se elevan al hover. Es exactamente la estética "plantilla generada por IA" que se quiere evitar. |
| **Dashboard** | Tendencia "+12 %" hardcodeada; badge "En tiempo real" con caché de 5 min; "Clientes activos" cuenta todos los clientes; saludo con emoji; 4 tarjetas de igual peso sin jerarquía; enlaces `<a href>` que recargan la SPA; sin selector de período. |
| **Header** | Breadcrumb de un nivel; campana con punto "no leído" permanente sin funcionalidad; sin búsqueda global, sin selector de empresa/sucursal, sin menú de usuario. |
| **Sidebar** | Correcto estructuralmente. El botón de cerrar sesión solo aparece al pasar el ratón (inaccesible en tablet/táctil). No filtra por rol. |
| **Tablas** | Cada página implementa la suya; sin componente común, sin ordenamiento visible, sin paginación (solo 20 registros), sin selección, sin columnas alineadas a la derecha para cifras de forma consistente, scroll horizontal en móvil. |
| **Formularios** | Todos en modales, incluido el de factura con líneas (estrecho). Sin agrupación por secciones, sin ayudas contextuales. |
| **Feedback** | No hay sistema de toasts: crear/editar/borrar no confirma nada; los errores de mutación no se muestran. Borrado con `confirm()` nativo (5 lugares). |
| **Carga** | Mezcla de skeletons (páginas nuevas) y spinners (heredadas). |
| **Vacíos** | `EmptyState` existe pero las páginas heredadas muestran texto plano. |
| **Accesibilidad** | Botones-icono sin `aria-label`, modal sin focus trap, contraste de textos `zinc-400` sobre blanco por debajo de AA en tamaños pequeños. |
| **Tipografía** | Inter cargada con `@import` bloqueante; `tabular-nums` aplicado solo en algunas cifras. |

### 15.2 Principios de diseño

1. **Calma operativa.** Superficies planas, bordes de 1 px, una sola sombra (para capas flotantes). El color se reserva para significado (estado, alerta, acción primaria), no para decorar.
2. **Las cifras son las protagonistas.** Tipografía numérica tabular en todo el producto, alineación a la derecha, formato COP consistente desde un único helper.
3. **Jerarquía antes que cantidad.** Un dashboard con 4 KPIs principales + 1 bloque "requiere atención" vale más que 12 tarjetas.
4. **Diseñado para el mostrador.** El POS se diseña *tablet-first*, con objetivos táctiles ≥ 44 px, operable con teclado y lector de código de barras, y tolerante a manos con harina (sin gestos finos).
5. **Cada acción tiene respuesta.** Optimistic UI donde sea seguro, toasts con "deshacer" donde sea posible, confirmaciones solo para acciones destructivas o irreversibles (con el nombre del objeto y la consecuencia).
6. **Nada de datos inventados.** Si no hay datos suficientes, se dice y se explica cómo obtenerlos.

### 15.3 Identidad: GestorPro + Miga

- **Arquitectura de marca:** *endorsed brand*. "GestorPro" es la marca paraguas; "Miga" el producto. Lockup: **Miga** en wordmark principal + "by GestorPro" en peso menor. Login, emails y facturas muestran ambos.
- **Paleta propuesta (a validar con prototipo):**
  - *Neutros:* escala gris cálida-neutra (no beige) como base de superficies y texto.
  - *Primario GestorPro:* un azul tinta profundo, sobrio y "financiero" — reemplaza el índigo/violeta saturado.
  - *Acento Miga:* un **ámbar/miel** usado con moderación (estado activo, foco del POS, highlights de marca). Remite al horneado sin caer en marrones ni beige, y sobre neutros fríos se ve tecnológico.
  - *Semánticos:* éxito, alerta, peligro, info — independientes de la marca.
  - Los verticales futuros cambian **solo el acento** (restaurantes, cafeterías…), conservando primario y neutros: una familia visual reconocible.
- **Tipografía:** una sans geométrica-humanista con cifras tabulares de calidad (Inter se mantiene como opción segura; evaluar *Geist* o *Inter Display* para titulares), autoalojada.
- **Iconografía:** lucide (ya en uso), trazo 1,5 px, sin iconos dentro de círculos de color.
- **Ilustración:** mínima, lineal, solo en estados vacíos y onboarding. Nada de panes dibujados en la UI operativa.

### 15.4 Sistema de diseño (tokens → primitivas → patrones)

- **Tokens** (CSS variables vía `@theme` de Tailwind): color semántico (`--color-surface`, `--color-surface-raised`, `--color-border`, `--color-text`, `--color-text-muted`, `--color-accent`, `--color-success`…), espaciado en escala de 4 px, radios (6/10/14), una sombra de elevación, duraciones de movimiento. Modo claro y oscuro por tokens, no por clases `dark:` repetidas en cada componente.
- **Primitivas:** Button, IconButton, Input, NumberInput/MoneyInput, Select/Combobox, Checkbox, Switch, Textarea, DatePicker/PeriodPicker, Badge, Tooltip, Popover, Dropdown, Tabs, Dialog, Drawer, Toast, Skeleton, Avatar, Kbd.
- **Patrones:** `PageHeader` (título, descripción, acciones), `DataTable` (orden, filtros, paginación de servidor, selección, columnas numéricas, estado vacío/carga/error, vista de tarjetas en móvil), `FilterBar` con chips, `KpiTile` (valor, variación, comparación, sparkline opcional), `ChartCard`, `AttentionList`, `EmptyState` (con acción primaria), `ConfirmDialog`, `FormSection`, `MoneyDisplay`.
- **Gráficos:** envoltorio sobre Recharts con paleta categórica validada en claro/oscuro, ejes discretos, comparación de período como serie tenue, tooltips con formato COP.
- **Documentación:** página interna `/design` (o Storybook si el equipo crece) con cada componente y estado.

### 15.5 Navegación propuesta (Miga)

```
[Miga by GestorPro]   [Panadería La Espiga ▾ / Sede Centro ▾]           [⌘K Buscar]  [?]  [Avatar ▾]

OPERACIÓN
  ◉ Inicio
  ◉ Vender                (POS a pantalla completa; atajo F2)
  ◉ Caja
  ◉ Ventas
PRODUCCIÓN
  ◉ Producción
  ◉ Recetas
  ◉ Mermas
INVENTARIO
  ◉ Productos
  ◉ Ingredientes
  ◉ Movimientos
  ◉ Compras
FINANZAS
  ◉ Gastos
  ◉ Reportes
DIRECTORIO
  ◉ Clientes
  ◉ Proveedores
──────────
  ⚙ Configuración        (Empresa · Sucursales · Usuarios y roles · Pagos e impuestos · Plan)
```

- El **cajero** ve solo *Vender, Caja, Mermas* y entra directamente al POS tras el login.
- **Paleta de comandos (⌘K):** buscar producto, cliente, venta por número; acciones rápidas ("Registrar merma", "Nueva producción").
- **Super Admin:** aplicación separada en `/platform` con su propio layout (Empresas, Usuarios, Planes, Suscripciones, Actividad, Métricas). Nunca aparece en la navegación de un tenant.

---

## 16. Riesgos técnicos

| # | Riesgo | Prob. | Impacto | Mitigación |
|---|---|:-:|:-:|---|
| R1 | Fuga entre tenants por consulta sin filtro | Media | **Crítico** | 5 capas (§11.2), test de aislamiento en CI, RLS |
| R2 | Inconsistencia venta↔caja↔inventario por fallos parciales o concurrencia | Media | Alto | Servicios con `atomic`, `select_for_update`, libros inmutables, tests de concurrencia |
| R3 | Costos de receta incorrectos por unidades mal convertidas | Alta | Alto | Unidades con dimensión, conversión centralizada y testeada, validación al crear recetas |
| R4 | POS lento o caído = la panadería no vende | Media | **Crítico** | POS con catálogo en caché, presupuesto de rendimiento (< 150 ms por acción), modo degradado; **modo offline como fase posterior explícita** |
| R5 | Requisitos fiscales DIAN para ventas POS (documento equivalente electrónico) | Alta | Alto | Diseñar `Sale` con numeración, resolución y campos fiscales desde el inicio; integración con proveedor tecnológico autorizado como fase propia. **Validar con un contador.** |
| R6 | Sobre-ingeniería del sistema de verticales antes de tener el segundo vertical | Media | Medio | Registro de módulos simple; abstraer solo lo que Miga usa; no construir restaurantes "por si acaso" |
| R7 | Reescritura que se alarga sin entregar valor visible | Media | Alto | Roadmap por incrementos demostrables; el POS usable llega en la Fase 7 |
| R8 | Reset de migraciones mal coordinado | Baja | Medio | Una sola vez, antes de tener clientes, con tu aprobación (D-1) |
| R9 | Reportes lentos con años de datos | Baja (inicio) | Medio | Índices por (tenant, fecha); tablas de resumen diario cuando haga falta |
| R10 | Plan gratuito de Railway (arranque en frío) | Alta | Medio | Plan de pago o proveedor con instancia siempre activa antes de clientes reales |
| R11 | Dependencia de un LLM externo con datos financieros del cliente | Media | Medio | Módulo opcional, consentimiento por tenant, datos agregados (no PII), registro de uso |

---

## 17. Roadmap

Cada fase termina con algo **demostrable** y con tests. Estimaciones relativas (S/M/L), no fechas, hasta que acordemos dedicación.

| Fase | Entregable | Tamaño | Depende de |
|---|---|:-:|---|
| **0. Contención** *(propuesta de urgencia, opcional)* | Quitar superusuario al demo, quitar `wipe_db` del arranque de producción **o** documentar que el entorno es de demostración, validar FKs por tenant en billing | S | — |
| **1. Auditoría** | Este documento | ✓ | — |
| **2. Arquitectura SaaS** | ADRs (decisiones), estructura de carpetas, settings por entorno, Postgres en Docker, CI (lint, tipos, tests), kernel (`Money`, `TenantModel`, servicios, secuencias) | M | Aprobación |
| **3. Multi-tenancy** | `Tenant`, `Location`, `Membership`, contexto de tenant, managers que fallan cerrado, campos FK tenant-aware, JWT con `tid` + cookie httpOnly + blacklist, test de aislamiento | M | 2 |
| **4. Core/Vertical/Platform** | Roles y permisos, auditoría, registro de módulos (backend y frontend), entitlements por plan, `VerticalDefinition` de Miga, migración de clientes/proveedores/categorías al Core | L | 3 |
| **5. Sistema de diseño** | Tokens, primitivas, `DataTable`, `PageHeader`, toasts, `ConfirmDialog`, `PeriodPicker`, gráficos; identidad Miga; migración del layout; página `/design` | L | 2 (en paralelo con 3–4) |
| **6. Módulos Miga base** | Catálogo (productos/ingredientes/unidades), clientes, proveedores, configuración, onboarding del vertical, **datos demo de panadería colombiana** | M | 4, 5 |
| **7. POS + Caja** | POS tablet-first, pagos mixtos, sesiones de caja, arqueo, anulaciones, devoluciones, ticket | L | 6 |
| **8. Inventario y producción** | Libro de movimientos, compras, recetas versionadas, lotes de producción, mermas, kardex, conteo físico, descarga por receta | L | 6 |
| **9. Reportes y analítica** | Dashboard de Miga, reportes §14.3, comparación de períodos, exportación | L | 7, 8 |
| **10. Administración SaaS** | Panel Super Admin, planes, suscripciones, límites, métricas globales, impersonación auditada | M | 4 |
| **11. Testing** | Cobertura de servicios críticos, E2E (Playwright) de flujos venta→caja→inventario→reporte, tests de concurrencia | M | transversal desde la Fase 2 |
| **12. Seguridad** | RLS en Postgres, rate limiting, headers, revisión OWASP ASVS nivel 2, backups y restauración probada | M | 3 |
| **13. Optimización** | Índices, resúmenes diarios, caché de catálogo en POS, presupuesto de rendimiento, *code splitting* | M | 9 |
| **14. Refinamiento UX/UI** | Pruebas con usuarios reales (dueño + cajero), microinteracciones, accesibilidad AA, pulido | M | 9 |

> Testing y seguridad se listan como fases porque así lo pediste, pero **no se postergan**: cada fase incluye sus tests y sus controles de seguridad; las fases 11 y 12 son de endurecimiento y auditoría.

### 17.1 Primer incremento sugerido tras tu aprobación

Fase 2 + el núcleo de la Fase 3 en una misma rama: estructura, CI, kernel, `Tenant/Membership`, contexto de tenant y el test de aislamiento — **con el test fallando primero contra el código actual (S1) y pasando después**. Es el cimiento de todo lo demás y es verificable.

---

## Decisiones que necesito que apruebes

| ID | Decisión | Mi recomendación |
|---|---|---|
| **D-1** | ¿Podemos regenerar el historial de migraciones desde cero (no hay datos productivos persistentes)? | **Sí**, una única vez, ahora. |
| **D-2** | Nombre de la entidad tenant en el código | `Tenant` en código; "Empresa" en la UI. |
| **D-3** | ¿Sucursales (`Location`) desde el MVP? | **Sí** en el modelo; la UI de multi-sucursal se habilita por plan. |
| **D-4** | ¿Un usuario puede pertenecer a varias empresas? | **Sí** (`Membership`). |
| **D-5** | Estrategia de tenancy | Schema compartido + 5 capas (§11). |
| **D-6** | Ítem único con `kind` vs. tablas separadas Producto/Ingrediente | **Ítem único**, pantallas separadas. |
| **D-7** | Costeo | Costo promedio ponderado. |
| **D-8** | ¿Se mantiene el módulo de Facturación (cuentas por cobrar/cotizaciones) en Miga? | Sí, como módulo opcional; el POS es el flujo principal. |
| **D-9** | Empleados/RR. HH. y Asistente IA en el MVP de Miga | Fuera del MVP; se conservan como módulos opcionales. |
| **D-10** | Facturación electrónica DIAN | Preparar el modelo ahora; integración como fase propia tras validar con un contador. |
| **D-11** | Modo offline del POS | Fuera del MVP; diseñar el POS para permitirlo después. |
| **D-12** | Un único destino de despliegue (Railway sirviendo API + SPA) y retirar las configs de Vercel/Netlify | Sí. |
| **D-13** | ¿Aplicamos la Fase 0 (contención de seguridad) ya, antes de la Fase 2? | Sí, si la demo pública sigue en línea. |
| **D-14** | Paleta de marca (azul tinta + acento ámbar) | Validar con un prototipo del dashboard y del POS en la Fase 5. |
