from .catalog import ensure_default_categories
from .definition import MIGA


def on_tenant_provisioned(sender, tenant, **kwargs):
    """Configuración inicial de una panadería. Corre con el tenant activo, en la transacción del alta."""
    if tenant.vertical != MIGA.key:
        return
    ensure_default_categories()
