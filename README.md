# GestorPro

Sistema SaaS de gestión para pequeñas y medianas empresas (PYMEs). Permite administrar clientes, inventario y facturación desde una interfaz moderna y responsiva.

## Demo

> 🔗 URL del deploy (próximamente)

**Credenciales de prueba:**
- Email: `demo@gestorpro.com`
- Password: `demo1234`

## Funcionalidades

- **Autenticación JWT** — Login seguro con tokens de acceso y renovación automática
- **Gestión de clientes** — CRM con búsqueda, filtros, creación y edición
- **Inventario** — Productos y servicios con control de stock y alertas de stock bajo
- **Facturación** — Facturas y cotizaciones con líneas de detalle, IVA y totales automáticos
- **Dashboard** — Métricas en tiempo real: cartera recaudada, pendiente y documentos emitidos
- **API REST documentada** — Swagger UI disponible en `/api/docs/`

## Stack tecnológico

### Backend
| Tecnología | Uso |
|---|---|
| Python 3.14 + Django 6 | Framework principal |
| Django REST Framework | API REST |
| SimpleJWT | Autenticación con tokens JWT |
| drf-spectacular | Documentación Swagger automática |
| SQLite (dev) / PostgreSQL (prod) | Base de datos |

### Frontend
| Tecnología | Uso |
|---|---|
| React 19 + TypeScript | UI |
| Vite | Bundler |
| Tailwind CSS | Estilos |
| TanStack Query | Caché y estado del servidor |
| Zustand | Estado global (auth) |
| React Hook Form + Zod | Formularios con validación |
| Axios | Cliente HTTP con interceptores JWT |

## Arquitectura

```
gestorpro/
├── backend/
│   ├── apps/
│   │   ├── users/       # Autenticación y roles
│   │   ├── clients/     # CRM de clientes
│   │   ├── billing/     # Facturas y cotizaciones
│   │   └── inventory/   # Productos y stock
│   └── config/          # Settings y URLs principales
└── frontend/
    └── src/
        ├── api/         # Servicios HTTP (axios)
        ├── components/  # Componentes reutilizables
        ├── pages/       # Vistas por módulo
        ├── store/       # Estado global (zustand)
        └── types/       # Interfaces TypeScript
```

## Instalación local

### Backend

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/gestorpro.git
cd gestorpro

# 2. Crear entorno virtual e instalar dependencias
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Edita .env con tus credenciales

# 4. Aplicar migraciones y crear superusuario
python manage.py migrate
python manage.py createsuperuser

# 5. Iniciar servidor
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

La app estará disponible en `http://localhost:5173`
La API estará disponible en `http://localhost:8000`
Documentación Swagger en `http://localhost:8000/api/docs/`

## API Endpoints

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/auth/login/` | Login → retorna tokens JWT |
| POST | `/api/auth/register/` | Registro de usuario |
| GET/PUT | `/api/auth/profile/` | Perfil del usuario autenticado |
| GET/POST | `/api/clients/` | Listar y crear clientes |
| GET/PUT/DELETE | `/api/clients/{id}/` | Detalle de cliente |
| GET/POST | `/api/inventory/products/` | Productos |
| GET/POST | `/api/inventory/categories/` | Categorías |
| GET | `/api/inventory/low-stock/` | Productos con stock bajo |
| GET/POST | `/api/billing/invoices/` | Facturas y cotizaciones |
| GET | `/api/billing/summary/` | Resumen para dashboard |

## Autor

**Juan Manuel** — Junior Developer  
📍 Bogotá, Colombia  
🔗 [LinkedIn](https://linkedin.com/in/tu-perfil) · [GitHub](https://github.com/tu-usuario)
