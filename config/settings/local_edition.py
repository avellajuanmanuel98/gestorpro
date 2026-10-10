"""
Edición local: GestorPro instalado en un computador del negocio y usado por la
red local (caja, tablet, celular del dueño). Lo arranca scripts/local_edition.py,
que define las variables de entorno (SECRET_KEY, DATABASE_URL, ALLOWED_HOSTS…).

Igual de cerrado que producción, salvo lo que exige HTTP en una red local:
no hay redirección a HTTPS, HSTS ni cookies "Secure" (no hay certificado).
"""
import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import LOGGING, SECRET_KEY

DEBUG = False

if len(SECRET_KEY) < 50 or SECRET_KEY.startswith('django-insecure'):
    raise ImproperlyConfigured('SECRET_KEY de la edición local debe ser aleatoria y de al menos 50 caracteres.')

AUDIT_TRUSTED_PROXY_COUNT = 0  # sin proxy: la IP del cliente es la de la conexión
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SECURE_CROSS_ORIGIN_OPENER_POLICY = None  # el navegador lo ignora sin HTTPS y solo llena la consola de avisos

# Imágenes subidas (productos, logo): fuera del código, dentro de la carpeta de datos (entran en las copias)
if os.environ.get('GESTORPRO_MEDIA_ROOT'):
    MEDIA_ROOT = os.environ['GESTORPRO_MEDIA_ROOT']
SERVE_MEDIA = True

# Registro en archivo (rotativo) además de la consola
_log_file = os.environ.get('GESTORPRO_LOG_FILE')
if _log_file:
    LOGGING['handlers']['file'] = {
        'class': 'logging.handlers.RotatingFileHandler', 'filename': _log_file,
        'maxBytes': 5 * 1024 * 1024, 'backupCount': 5, 'encoding': 'utf-8',
    }
    LOGGING['root']['handlers'] = [*LOGGING['root']['handlers'], 'file']
