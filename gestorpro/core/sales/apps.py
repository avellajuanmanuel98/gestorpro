from django.apps import AppConfig


class SalesConfig(AppConfig):
    name = 'gestorpro.core.sales'
    label = 'sales'
    verbose_name = 'Ventas (POS)'

    def ready(self):
        from gestorpro.core.tenancy.signals import tenant_provisioned

        from .services import ensure_pos_defaults

        tenant_provisioned.connect(lambda sender, tenant, **kw: ensure_pos_defaults(), weak=False,
                                   dispatch_uid='sales.pos_defaults')
