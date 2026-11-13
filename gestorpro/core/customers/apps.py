from django.apps import AppConfig


class CustomersConfig(AppConfig):
    name = 'gestorpro.core.customers'
    label = 'customers'
    verbose_name = 'Clientes'

    def ready(self):
        from gestorpro.core.tenancy.signals import tenant_provisioned

        from .services import ensure_final_consumer

        tenant_provisioned.connect(lambda sender, tenant, **kw: ensure_final_consumer(), weak=False,
                                   dispatch_uid='customers.final_consumer')
