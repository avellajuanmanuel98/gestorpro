import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, SECRET_KEY

DEBUG = False

# 40+ caracteres aleatorios: admite la clave de 256 bits que genera Render (44 caracteres en base64)
if len(SECRET_KEY) < 40 or len(set(SECRET_KEY)) < 10 or SECRET_KEY.startswith('django-insecure'):
    raise ImproperlyConfigured('SECRET_KEY de producción debe ser aleatoria y de al menos 40 caracteres.')

# Render publica la app en https://<servicio>.onrender.com y lo informa en RENDER_EXTERNAL_HOSTNAME:
# ese dominio se permite solo, y es el de los enlaces (invitaciones, contraseñas) si no se fijó otro.
_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
if _render_host:
    ALLOWED_HOSTS = [*ALLOWED_HOSTS, _render_host]
    CSRF_TRUSTED_ORIGINS = [*CSRF_TRUSTED_ORIGINS, f'https://{_render_host}']
    if not os.environ.get('FRONTEND_URL'):
        FRONTEND_URL = f'https://{_render_host}'

# Railway y Render terminan TLS en su proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
AUDIT_TRUSTED_PROXY_COUNT = 1
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r'^api/health/$']  # el chequeo de salud del proveedor llega por HTTP interno
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
