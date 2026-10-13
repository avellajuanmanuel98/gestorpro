"""
Emisión de tokens.

- access (15 min): viaja en el cuerpo de la respuesta y el frontend lo manda en
  la cabecera Authorization.
- refresh (7 días): SOLO en una cookie httpOnly (`gp_refresh`). El JavaScript de
  la página no puede leerla, así que un script inyectado no puede robar la
  sesión larga. SameSite=Strict y limitada a /api/auth/: el navegador no la
  envía desde otros sitios ni a otros endpoints.
"""
from urllib.parse import urlsplit

from django.conf import settings
from rest_framework.response import Response
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import TENANT_CLAIM

REFRESH_COOKIE = 'gp_refresh'
REFRESH_COOKIE_PATH = '/api/auth/'


def issue_tokens(user, tenant_id: int | None) -> dict:
    refresh = RefreshToken.for_user(user)
    if tenant_id is not None:
        refresh[TENANT_CLAIM] = tenant_id  # el access token hereda el claim
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


def token_response(user, tenant_id: int | None, http_status: int = 200) -> Response:
    """Respuesta de inicio de sesión: access en el cuerpo, refresh en la cookie."""
    tokens = issue_tokens(user, tenant_id)
    response = Response({'access': tokens['access']}, status=http_status)
    set_refresh_cookie(response, tokens['refresh'])
    return response


def set_refresh_cookie(response, refresh: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE, refresh, max_age=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        path=REFRESH_COOKIE_PATH, httponly=True, samesite='Strict',
        secure=getattr(settings, 'REFRESH_COOKIE_SECURE', True),
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, samesite='Strict')


def refresh_from(request) -> str | None:
    return request.COOKIES.get(REFRESH_COOKIE) or None


def same_origin(request) -> bool:
    """
    Defensa adicional a SameSite: si el navegador declara el origen, debe ser
    este mismo sitio (o uno de CSRF_TRUSTED_ORIGINS).
    """
    origin = request.headers.get('Origin')
    if not origin:
        return True  # sin Origin no hay contexto de otro sitio (curl, misma página antigua)
    if origin == 'null':
        return False
    parts = urlsplit(origin)
    if parts.netloc == request.get_host():
        return True
    return origin in getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])


def choose_tenant(user, memberships):
    """Última empresa usada si sigue activa; si no, la primera disponible."""
    ids = [m.tenant_id for m in memberships]
    if user.last_tenant_id in ids:
        return user.last_tenant_id
    return ids[0] if ids else None
