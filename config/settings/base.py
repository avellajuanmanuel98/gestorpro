"""
Configuración común a todos los entornos.

Entornos: dev.py (local), test.py (pytest/CI), prod.py (Railway).
PostgreSQL es el único motor soportado: no hay fallback a SQLite, para que
desarrollo, tests y producción se comporten igual (constraints, NUMERIC,
bloqueos de filas, y en el futuro Row-Level Security).
"""
from datetime import timedelta
from pathlib import Path

import dj_database_url
from decouple import config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

GROQ_API_KEY = config('GROQ_API_KEY', default='')


# ─────────────────────────────────────────────
# APLICACIONES — organizadas por capa
#   kernel        utilidades sin dominio (dinero, API base)
#   core          funcionalidades comunes a cualquier PYME
#   capabilities  módulos reutilizables y activables
#   verticals     configuración y features por tipo de negocio
#   platform      administración global de GestorPro (SaaS)
# Las dependencias entre capas se verifican en CI (import-linter, .importlinter).
# ─────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
]

LOCAL_APPS = [
    # core
    'gestorpro.core.tenancy',
    'gestorpro.core.identity',
    'gestorpro.core.access',
    'gestorpro.core.audit',
    'gestorpro.core.customers',
    'gestorpro.core.suppliers',
    'gestorpro.core.catalog',
    'gestorpro.core.billing',
    'gestorpro.core.numbering',
    'gestorpro.core.cash',
    'gestorpro.core.sales',
    'gestorpro.core.reporting',
    # capabilities
    'gestorpro.capabilities.hr',
    'gestorpro.capabilities.assistant',
    # verticals
    'gestorpro.verticals.bakery',
    # platform
    'gestorpro.platform.subscriptions',
    'gestorpro.platform.admin_panel',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # Garantiza que el contexto de tenant nunca sobreviva entre peticiones
    'gestorpro.core.tenancy.middleware.TenantContextMiddleware',
    'gestorpro.core.audit.context.AuditContextMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ─────────────────────────────────────────────
# BASE DE DATOS — solo PostgreSQL
# ─────────────────────────────────────────────
DATABASE_URL = config('DATABASE_URL', default='')
if not DATABASE_URL.startswith(('postgres://', 'postgresql://')):
    raise ImproperlyConfigured(
        'DATABASE_URL debe apuntar a PostgreSQL (postgres://...). '
        'En local: docker compose up -d db'
    )
DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)}


AUTH_USER_MODEL = 'identity.User'

# URL pública del frontend (enlaces de invitación)
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:5173')

# Plan con el que arranca (en prueba) toda empresa nueva
DEFAULT_PLAN_CODE = config('DEFAULT_PLAN_CODE', default='starter')

# Diferencia de caja (COP) por encima de la cual el cierre lo debe hacer un supervisor
CASH_DIFFERENCE_TOLERANCE = config('CASH_DIFFERENCE_TOLERANCE', default='5000')

# Proxies de confianza delante de la app (para la IP real en auditoría). 0 en local.
AUDIT_TRUSTED_PROXY_COUNT = config('AUDIT_TRUSTED_PROXY_COUNT', default=0, cast=int)


# ─────────────────────────────────────────────
# DJANGO REST FRAMEWORK
# Por defecto: autenticado + miembro activo de un tenant (fail-closed).
# Los endpoints públicos o de plataforma lo sobrescriben explícitamente.
# ─────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'gestorpro.core.identity.authentication.TenantJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'gestorpro.core.access.permissions.IsTenantMember',
    ),
    'DEFAULT_PAGINATION_CLASS': 'gestorpro.kernel.api.pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'gestorpro.kernel.api.exceptions.exception_handler',
    'COERCE_DECIMAL_TO_STRING': True,
    'DEFAULT_THROTTLE_RATES': {
        'auth': config('THROTTLE_AUTH', default='10/min'),
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}


CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://localhost:5174,http://localhost:3000'
).split(',')
CORS_ALLOW_HEADERS = [
    'accept', 'accept-encoding', 'authorization', 'content-type',
    'origin', 'x-csrftoken', 'x-requested-with',
]
CORS_EXPOSE_HEADERS = ['Content-Type']
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:5173,http://localhost:5174'
).split(',')


SPECTACULAR_SETTINGS = {
    'TITLE': 'GestorPro API',
    'DESCRIPTION': 'API REST multi-tenant de GestorPro',
    'VERSION': '2.0.0',
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

# WhiteNoise sirve el build de React desde la raíz del dominio
WHITENOISE_ROOT = BASE_DIR / 'frontend' / 'dist'
WHITENOISE_INDEX_FILE = True

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': config('LOG_LEVEL', default='INFO')},
}
