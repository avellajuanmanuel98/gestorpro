from .base import *  # noqa: F401,F403

DEBUG = True

# En desarrollo, si no hay servidor de correo, los correos se imprimen en la consola
if not EMAIL_ENABLED:  # noqa: F405
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_ENABLED = True
