from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AccessConfig(AppConfig):
    name = 'gestorpro.core.access'
    label = 'access'
    verbose_name = 'Roles y permisos'

    def ready(self):
        from .registry import sync_permissions
        post_migrate.connect(sync_permissions, sender=self)
