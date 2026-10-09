from django.apps import AppConfig


class BakeryConfig(AppConfig):
    name = 'gestorpro.verticals.bakery'
    label = 'bakery'
    verbose_name = 'Miga — panaderías'

    def ready(self):
        from gestorpro.core.tenancy.signals import tenant_provisioned

        from .signals import on_tenant_provisioned

        tenant_provisioned.connect(on_tenant_provisioned, dispatch_uid='bakery.on_tenant_provisioned')
