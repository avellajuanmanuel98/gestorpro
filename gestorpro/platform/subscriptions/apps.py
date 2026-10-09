from django.apps import AppConfig


class SubscriptionsConfig(AppConfig):
    name = 'gestorpro.platform.subscriptions'
    label = 'subscriptions'
    verbose_name = 'Planes y suscripciones'

    def ready(self):
        from gestorpro.core import entitlements
        from gestorpro.core.tenancy.signals import tenant_provisioned

        from .services import entitlements_for, on_tenant_provisioned

        entitlements.register_provider(entitlements_for)
        tenant_provisioned.connect(on_tenant_provisioned, dispatch_uid='subscriptions.on_tenant_provisioned')
