"""
Configuración común a todos los entornos.

Entornos: dev.py (local), test.py (pytest/CI), prod.py (Railway).
PostgreSQL es el único motor soportado: no hay fallback a SQLite, para que
desarrollo, tests y producción se comporten igual (constraints, NUMERIC,
bloqueos de filas y Row-Level Security).
"""
from datetime import timedelta
from pathlib import Path

import dj_database_url
from decouple import config
from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP, build_policy

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
    'gestorpro.core.inventory',
    'gestorpro.core.purchasing',
    'gestorpro.core.analytics',
    'gestorpro.core.reporting',
    # capabilities
    'gestorpro.capabilities.hr',
    'gestorpro.capabilities.assistant',
    'gestorpro.capabilities.production',
    'gestorpro.capabilities.waste',
    # verticals
    'gestorpro.verticals.bakery',
    # platform
    'gestorpro.platform.subscriptions',
    'gestorpro.platform.admin_panel',
    'gestorpro.platform.console',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.csp.ContentSecurityPolicyMiddleware',
    'gestorpro.kernel.api.middleware.NoStoreApiMiddleware',
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

# Correo (recuperar contraseña). Sin EMAIL_HOST no se envía nada: la edición local y
# cualquier instalación sin correo usan enlaces que genera el dueño o la plataforma.
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='GestorPro <no-responder@gestorpro.co>')
EMAIL_ENABLED = bool(EMAIL_HOST)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_TIMEOUT = 15
# Enlaces para crear una contraseña nueva: válidos 24 h y de un solo uso
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24

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
    # Límites de uso: por IP sin sesión, por usuario con sesión; más estrictos en lo sensible
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'auth': config('THROTTLE_AUTH', default='10/min'),            # login, registro, contraseñas, invitaciones
        'refresh': config('THROTTLE_REFRESH', default='30/min'),      # renovar la sesión
        'sensitive': config('THROTTLE_SENSITIVE', default='10/min'),  # cambiar la contraseña con sesión
        'anon': config('THROTTLE_ANON', default='120/min'),
        'user': config('THROTTLE_USER', default='1200/min'),
    },
}
# Bloqueo por cuenta (core/identity/lockout.py)
LOGIN_LOCKOUT_FAILURES = config('LOGIN_LOCKOUT_FAILURES', default=5, cast=int)
LOGIN_LOCKOUT_MINUTES = config('LOGIN_LOCKOUT_MINUTES', default=15, cast=int)

# Cookie httpOnly del refresh token (core/identity/tokens.py): Secure salvo en desarrollo y edición local
REFRESH_COOKIE_SECURE = config('REFRESH_COOKIE_SECURE', default=True, cast=bool)

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


# /api/docs/ y /api/schema/: siempre en desarrollo; en otros entornos solo si se habilita a propósito
API_DOCS_ENABLED = config('API_DOCS_ENABLED', default=False, cast=bool)
SPECTACULAR_SETTINGS = {
    'TITLE': 'GestorPro API',
    'DESCRIPTION': 'API REST multi-tenant de GestorPro',
    'VERSION': '2.0.0',
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    # 12 caracteres como mínimo (OWASP ASVS 2.1.1); aplica a contraseñas nuevas, no a las ya guardadas
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
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


# Content Security Policy: solo código y recursos del propio GestorPro. Sin scripts en
# línea ni eval, sin marcos de otros sitios, sin enviar formularios a otro lado. Si
# alguien lograra inyectar HTML, el navegador no ejecutaría su script ni lo dejaría
# enviar datos afuera.
SECURE_CSP = {
    'default-src': [CSP.SELF],
    'script-src': [CSP.SELF],
    'style-src': [CSP.SELF],
    'img-src': [CSP.SELF, 'data:', 'blob:'],
    'font-src': [CSP.SELF, 'data:'],
    'connect-src': [CSP.SELF],
    'object-src': [CSP.NONE],
    'base-uri': [CSP.SELF],
    'form-action': [CSP.SELF],
    'frame-ancestors': [CSP.NONE],
}
PERMISSIONS_POLICY = 'camera=(), microphone=(), geolocation=(), payment=(), usb=()'


def _whitenoise_headers(headers, path, url):
    # WhiteNoise sirve index.html sin pasar por los middlewares de Django: las mismas cabeceras aquí
    if path.endswith('.html'):
        headers['Content-Security-Policy'] = build_policy(SECURE_CSP)
        headers['X-Frame-Options'] = 'DENY'
        headers['X-Content-Type-Options'] = 'nosniff'
        headers['Referrer-Policy'] = 'same-origin'
        headers['Permissions-Policy'] = PERMISSIONS_POLICY


WHITENOISE_ADD_HEADERS_FUNCTION = _whitenoise_headers

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': config('LOG_LEVEL', default='INFO')},
}
