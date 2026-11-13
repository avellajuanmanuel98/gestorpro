"""
Contexto de auditoría de la petición en curso: quién actúa y desde dónde.

Lo inicializa AuditContextMiddleware (IP, user agent) y lo completa la
autenticación (actor). Fuera de una petición (comandos, tareas) el actor es
"sistema".
"""
from contextvars import ContextVar
from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class AuditContext:
    actor_id: int | None = None
    actor_label: str = 'sistema'
    ip: str | None = None
    user_agent: str = ''


_context: ContextVar[AuditContext] = ContextVar('audit_context', default=AuditContext())  # noqa: B039 (dataclass inmutable)


def current() -> AuditContext:
    return _context.get()


def client_ip(request) -> str | None:
    """
    IP del cliente. Detrás de un proxy de confianza (Railway) se toma la
    entrada que añadió ese proxy en X-Forwarded-For, no la que envía el
    cliente (que podría falsificarla).
    """
    proxies = getattr(settings, 'AUDIT_TRUSTED_PROXY_COUNT', 0)
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if proxies and forwarded:
        hops = [h.strip() for h in forwarded.split(',') if h.strip()]
        if len(hops) >= proxies:
            return hops[-proxies]
    return request.META.get('REMOTE_ADDR')


def bind_request(request):
    return _context.set(AuditContext(
        ip=client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:300],
    ))


def bind_actor(user):
    ctx = _context.get()
    _context.set(AuditContext(actor_id=user.pk, actor_label=user.email, ip=ctx.ip, user_agent=ctx.user_agent))


def reset(token):
    _context.reset(token)


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = bind_request(request)
        try:
            return self.get_response(request)
        finally:
            reset(token)
