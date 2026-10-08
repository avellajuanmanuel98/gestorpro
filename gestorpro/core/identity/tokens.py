from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import TENANT_CLAIM


def issue_tokens(user, tenant_id: int | None) -> dict:
    refresh = RefreshToken.for_user(user)
    if tenant_id is not None:
        refresh[TENANT_CLAIM] = tenant_id  # el access token hereda el claim
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


def choose_tenant(user, memberships):
    """Última empresa usada si sigue activa; si no, la primera disponible."""
    ids = [m.tenant_id for m in memberships]
    if user.last_tenant_id in ids:
        return user.last_tenant_id
    return ids[0] if ids else None
