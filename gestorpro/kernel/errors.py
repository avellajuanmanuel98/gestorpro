class TenantIsolationError(Exception):
    """Base de todos los errores de aislamiento entre tenants."""


class TenantContextMissing(TenantIsolationError):
    """Se intentó acceder a datos de tenant sin un tenant activo (fail-closed)."""


class CrossTenantViolation(TenantIsolationError):
    """Se intentó leer, escribir o relacionar datos de un tenant distinto al activo."""
