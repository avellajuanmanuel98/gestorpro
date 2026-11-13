from django.apps import AppConfig


class WasteConfig(AppConfig):
    name = 'gestorpro.capabilities.waste'
    label = 'waste'
    verbose_name = 'Mermas'

    def ready(self):
        from gestorpro.core.tenancy.signals import tenant_provisioned

        from .services import ensure_default_reasons

        tenant_provisioned.connect(lambda sender, tenant, **kw: ensure_default_reasons(), weak=False,
                                   dispatch_uid='waste.default_reasons')
