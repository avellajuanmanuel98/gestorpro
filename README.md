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

**Credenciales de prueba:**

```
Email:    demo@gestorpro.com
Password: demo1234
```

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

Algunas elecciones que vale la pena explicar:

- **TanStack Query en lugar de estado global para datos del servidor.** El caché, la invalidación y los reintentos quedan resueltos por la librería; Zustand se reserva únicamente para el estado de autenticación, que sí es global y sincrónico.
- **Interceptores de Axios para el refresh de tokens.** La renovación del JWT es transparente para los componentes: ninguna vista necesita saber que el token expiró.
- **Validación duplicada con Zod y DRF serializers.** Zod da retroalimentación inmediata en el formulario; los serializers garantizan que la API no confíe en el cliente.
- **SQLite en desarrollo, PostgreSQL en producción.** Arranque local sin dependencias externas, sin renunciar a un motor real en producción.
- **Apps de Django por dominio** (`users`, `clients`, `billing`, `inventory`) en lugar de una app monolítica, para mantener los límites del modelo de negocio explícitos.

## Stack tecnológico

### Backend

| Tecnología | Uso |
|---|---|
| Python 3.14 + Django 6 | Framework principal |
| Django REST Framework | API REST |
| SimpleJWT | Autenticación con tokens JWT |
| drf-spectacular | Documentación OpenAPI/Swagger automática |
| SQLite (dev) / PostgreSQL (prod) | Base de datos |
| Railway | Despliegue del backend |

### Frontend

| Tecnología | Uso |
|---|---|
| React 19 + TypeScript | UI |
| Vite | Bundler y servidor de desarrollo |
| Tailwind CSS | Estilos |
| TanStack Query | Caché y estado del servidor |
| Zustand | Estado global (autenticación) |
| React Hook Form + Zod | Formularios con validación tipada |
| Axios | Cliente HTTP con interceptores JWT |
| Vercel | Despliegue del frontend |

## Arquitectura

```
gestorpro/
├── backend/
│   ├── apps/
│   │   ├── users/        # Autenticación y roles
│   │   ├── clients/      # CRM de clientes
│   │   ├── billing/      # Facturas y cotizaciones
│   │   └── inventory/    # Productos y stock
│   └── config/           # Settings y URLs principales
└── frontend/
    └── src/
        ├── api/          # Servicios HTTP (axios)
        ├── components/   # Componentes reutilizables
        ├── pages/        # Vistas por módulo
        ├── store/        # Estado global (zustand)
        └── types/        # Interfaces TypeScript
```

El frontend consume la API por HTTP; no hay renderizado en servidor ni acoplamiento entre ambos despliegues, lo que permite versionarlos y desplegarlos por separado.

## Instalación local

**Requisitos:** Python 3.14+, Node.js 20+, y opcionalmente PostgreSQL.

### 1. Clonar el repositorio

```bash
git clone https://github.com/avellajuanmanuel98/gestorpro.git
cd gestorpro
```

### 2. Backend

```bash
cd backend

# Entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt

# Variables de entorno
cp .env.example .env           # copy .env.example .env en Windows

# Base de datos y usuario administrador
python manage.py migrate
python manage.py createsuperuser

python manage.py runserver
```

### 3. Frontend

En otra terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

| Servicio | URL |
|---|---|
| Aplicación | http://localhost:5173 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/api/docs/ |
| Admin de Django | http://localhost:8000/admin/ |

### Variables de entorno

<!-- Ajusta esta tabla a los nombres reales de tu .env.example -->

**`backend/.env`**

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave secreta de Django |
| `DEBUG` | `True` en desarrollo, `False` en producción |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por comas |
| `DATABASE_URL` | Cadena de conexión de PostgreSQL (opcional en dev) |
| `CORS_ALLOWED_ORIGINS` | Origen del frontend |

**`frontend/.env`**

| Variable | Descripción |
|---|---|
| `VITE_API_URL` | URL base de la API |

## API

Documentación interactiva completa en [`/api/docs/`](https://web-production-cd18a.up.railway.app/api/docs/). Endpoints principales:

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/auth/login/` | Login → retorna tokens JWT |
| `POST` | `/api/auth/register/` | Registro de usuario |
| `GET` `PUT` | `/api/auth/profile/` | Perfil del usuario autenticado |
| `GET` `POST` | `/api/clients/` | Listar y crear clientes |
| `GET` `PUT` `DELETE` | `/api/clients/{id}/` | Detalle de cliente |
| `GET` `POST` | `/api/inventory/products/` | Productos |
| `GET` `POST` | `/api/inventory/categories/` | Categorías |
| `GET` | `/api/inventory/low-stock/` | Productos con stock bajo |
| `GET` `POST` | `/api/billing/invoices/` | Facturas y cotizaciones |
| `GET` | `/api/billing/summary/` | Resumen para el dashboard |

Todos los endpoints excepto `login` y `register` requieren la cabecera `Authorization: Bearer <access_token>`.

## Roadmap

- [ ] Exportación de facturas a PDF
- [ ] Reportes de ventas por período
- [ ] Multi-tenencia por empresa
- [ ] Suite de pruebas automatizadas (pytest + Vitest)
- [ ] CI en GitHub Actions

## Autor

**Juan Manuel García Avella** — Ingeniero de Sistemas · Desarrollador de Software
📍 Bogotá, Colombia

[LinkedIn](https://www.linkedin.com/in/juan-manuel-garc%C3%ADa-avella-/) · [GitHub](https://github.com/avellajuanmanuel98)

## Licencia

<!-- Añade un archivo LICENSE al repositorio y ajusta esta línea -->
Distribuido bajo licencia MIT.
