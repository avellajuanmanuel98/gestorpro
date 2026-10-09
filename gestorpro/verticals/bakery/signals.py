from gestorpro.core.catalog.models import Category

from .definition import MIGA


def on_tenant_provisioned(sender, tenant, **kwargs):
    """Configuración inicial de una panadería. Corre con el tenant activo, en la transacción del alta."""
    if tenant.vertical != MIGA.key:
        return
    for name in MIGA.default_categories:
        Category.objects.get_or_create(name=name)
