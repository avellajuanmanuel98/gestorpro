# GestorPro

**Mini-ERP SaaS para PYMEs** — clientes, inventario y facturación en una sola aplicación web, construida y desplegada de extremo a extremo.

[![Demo](https://img.shields.io/badge/demo-en%20vivo-22c55e?style=flat-square)](https://gestorpro-lac.vercel.app)
[![API Docs](https://img.shields.io/badge/API-Swagger-85EA2D?style=flat-square&logo=swagger&logoColor=black)](https://web-production-cd18a.up.railway.app/api/docs/)
![Django](https://img.shields.io/badge/Django-6.0-092E20?style=flat-square&logo=django)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white)

---

## El problema

Las PYMEs suelen gestionar clientes en una hoja de cálculo, inventario en otra y facturación en un talonario o en Word. La información se duplica, el stock nunca cuadra y no hay forma rápida de saber cuánto dinero está pendiente de cobro.

**GestorPro unifica esos tres flujos** en un único sistema con autenticación por roles, control de stock automático al facturar y un dashboard con métricas de cartera en tiempo real.

## Demo en vivo

| | |
|---|---|
| **Aplicación** | https://gestorpro-lac.vercel.app |
| **API + Swagger** | https://web-production-cd18a.up.railway.app/api/docs/ |

> [!IMPORTANT]
> La demo ya no expone credenciales públicas. Para probar la aplicación en local
> ejecuta `seed_demo` (ver *Instalación local*); la contraseña se define con la
> variable `DEMO_PASSWORD` o se genera aleatoriamente y se imprime en consola.

> [!NOTE]
> El backend está en el plan gratuito de Railway. La primera petición puede tardar unos segundos mientras el servicio arranca.

## Capturas

<!-- Reemplaza estas rutas por tus imágenes reales en /docs/screenshots/ -->
<!-- Sugerencia: dashboard, listado de facturas con detalle, y alerta de stock bajo -->

| Dashboard | Facturación |
|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Facturación](docs/screenshots/facturacion.png) |

## Funcionalidades

- **Autenticación JWT** — Login seguro con tokens de acceso y refresh automático mediante interceptores de Axios.
- **Gestión de clientes** — CRM con búsqueda, filtros, creación y edición.
- **Inventario** — Productos y servicios con control de stock y alertas de stock bajo.
- **Facturación** — Facturas y cotizaciones con líneas de detalle, cálculo automático de IVA y totales.
- **Dashboard** — Métricas en tiempo real: cartera recaudada, cartera pendiente y documentos emitidos.
- **API REST documentada** — Esquema OpenAPI generado automáticamente y Swagger UI en `/api/docs/`.

## Decisiones técnicas

- **Multi-tenant fail-closed.** Todas las tablas de negocio tienen `tenant_id`. El manager por defecto filtra por la empresa activa y **lanza un error si no hay una**: un descuido produce un error, no una fuga de datos. Detalle en [`docs/miga/02-arquitectura-multitenant.md`](docs/miga/02-arquitectura-multitenant.md).
- **Usuarios multiempresa y roles por empresa.** Un usuario puede pertenecer a varias empresas con un rol distinto en cada una. Los permisos se validan en backend por método HTTP; el frontend solo los usa para adaptar la interfaz.
- **Capas Platform / Core / Capabilities / Verticals**, con contratos de importación verificados en CI (`lint-imports`).
- **El servidor calcula el dinero.** `Decimal` con un único redondeo; los importes viajan como string. Precio e impuesto salen del catálogo y cambiarlos exige permiso.
- **PostgreSQL en todos los entornos** (desarrollo, tests y producción), sin SQLite.
- **TanStack Query** para estado del servidor; **Zustand** solo para la sesión.

## Stack tecnológico

| Backend | Frontend |
|---|---|
| Python 3.13 + Django 6 + DRF | React 19 + TypeScript + Vite |
| SimpleJWT (rotación + lista negra) | Tailwind CSS 4 |
| PostgreSQL 16 | TanStack Query + Zustand |
| drf-spectacular (OpenAPI) | React Hook Form + Zod, Recharts |
| pytest + ruff + import-linter | ESLint |

## Arquitectura

```
gestorpro/
├── config/settings/        base · dev · test · prod
├── gestorpro/
│   ├── kernel/             dinero, paginación, errores
│   ├── core/               tenancy · identity · access · audit · customers · suppliers · catalog · billing · reporting
│   ├── capabilities/       hr · assistant (IA)
│   ├── verticals/bakery/   Miga — panaderías
│   └── platform/           subscriptions (planes) · admin_panel (/admin/)
├── tests/                  isolation · architecture · core
├── frontend/src/           api · components · pages · store · lib · types
└── docs/miga/              auditoría y decisiones de arquitectura
```

## Instalación local

> ¿Instalar GestorPro **en el computador de un negocio** (sin nube, usado por la red local)? Ver la [edición local](docs/miga/09-edicion-local.md): `local\1-instalar.bat`. Esta sección es para desarrollo.

**Requisitos:** Python 3.13, Node.js 22, Docker (para PostgreSQL).

```bash
git clone https://github.com/avellajuanmanuel98/gestorpro.git
cd gestorpro

# Base de datos (PostgreSQL 16)
docker compose up -d db

# Backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                               # y define SECRET_KEY
python manage.py migrate
python manage.py seed_demo --password "Elige-una-1"   # panadería demo (solo DEBUG)
python manage.py runserver

# Frontend (otra terminal)
cd frontend && npm ci && npm run dev
```

### Windows (CMD)

```bat
git fetch origin
git checkout claude/zen-johnson-hhz8hm

:: PostgreSQL: Docker Desktop (o PostgreSQL 16 instalado nativamente, ver abajo)
docker compose up -d db

python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
:: Edita .env y define SECRET_KEY (cualquier texto largo en local)

python manage.py migrate
python manage.py seed_demo --password "Elige-una-1"
python manage.py runserver
```

En otra ventana: `cd frontend`, `npm ci`, `npm run dev`.

**Sin Docker:** instala PostgreSQL 16 para Windows, crea la base
(`createdb -U postgres gestorpro`) y en `.env` usa
`DATABASE_URL=postgres://postgres:TU_CLAVE@localhost:5432/gestorpro`.

| Servicio | URL |
|---|---|
| Aplicación | http://localhost:5173 |
| API / Swagger | http://localhost:8000/api/docs/ |
| Consola de plataforma | http://localhost:8000/admin/ (requiere `createsuperuser`) |

### Tests y verificaciones (las mismas que el CI)

```bash
ruff check .
lint-imports                                   # contratos de capas
python manage.py makemigrations --check --dry-run
pytest -m isolation                            # aislamiento entre empresas (obligatorio)
pytest                                         # suite completa
cd frontend && npm run lint && npm test && npm run build
```

### Variables de entorno

Ver [`.env.example`](.env.example). Las imprescindibles: `SECRET_KEY` y `DATABASE_URL` (PostgreSQL).

## API

Documentación interactiva en `/api/docs/`. Todos los endpoints de negocio operan sobre la **empresa activa** del token y exigen un permiso por método.

| Grupo | Endpoints |
|---|---|
| Sesión | `auth/register` · `auth/login` · `auth/token/refresh` · `auth/logout` · `auth/me` · `auth/switch-tenant` · `auth/change-password` |
| Empresa | `tenant/` · `tenant/locations/` · `tenant/plan/` |
| Usuarios y roles | `access/members/` · `access/invitations/` · `access/roles/` · `access/permissions/` · `auth/invitation/{token}` · `auth/accept-invitation/` |
| Auditoría | `audit/` |
| Core | `customers/` · `suppliers/` · `catalog/products/` · `catalog/categories/` · `catalog/low-stock/` · `billing/invoices/` · `billing/summary/` · `reports/billing/` · `reports/inventory/` |
| Capabilities | `employees/` · `reports/hr/` · `assistant/chat/` |

Los listados devuelven `count`, `page`, `page_size`, `total_pages` y `results` (máximo 100 por página).

## Roadmap

GestorPro está evolucionando hacia una plataforma SaaS para PYMES con verticales especializados; el primero es **Miga** (panaderías). Plan completo en [`docs/miga/01-auditoria-y-arquitectura.md`](docs/miga/01-auditoria-y-arquitectura.md).

- [x] Fase 0 — Contención de seguridad del despliegue
- [x] Fases 2–3 — Arquitectura por capas, multi-tenancy fail-closed, roles y permisos, CI
- [x] Fase 4 — Auditoría, gestión de usuarios y roles, planes ([detalle](docs/miga/03-fase-4-acceso-auditoria-planes.md))
- [x] Fase 5 — Sistema de diseño y unificación visual ([detalle](docs/miga/04-fase-5-sistema-de-diseno.md))
- [ ] Fases 6–9 — Miga: catálogo e ingredientes, POS y caja, inventario y producción, analítica

## Autor

**Juan Manuel García Avella** — Ingeniero de Sistemas · Desarrollador de Software
📍 Bogotá, Colombia

[LinkedIn](https://www.linkedin.com/in/juan-manuel-garc%C3%ADa-avella-/) · [GitHub](https://github.com/avellajuanmanuel98)

## Licencia

<!-- Añade un archivo LICENSE al repositorio y ajusta esta línea -->
Distribuido bajo licencia MIT.
