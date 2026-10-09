from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import SECRET_KEY

DEBUG = False

if len(SECRET_KEY) < 50 or SECRET_KEY.startswith('django-insecure'):
    raise ImproperlyConfigured('SECRET_KEY de producción debe ser aleatoria y de al menos 50 caracteres.')

# Railway termina TLS en su proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
AUDIT_TRUSTED_PROXY_COUNT = 1
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'
