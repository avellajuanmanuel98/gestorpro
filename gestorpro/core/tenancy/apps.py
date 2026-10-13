from django.apps import AppConfig


class TenancyConfig(AppConfig):
    name = 'gestorpro.core.tenancy'
    label = 'tenancy'
    verbose_name = 'Empresas (tenants)'

    def ready(self):
        from django.core.management.commands import flush, makemigrations, migrate, showmigrations
        from django.db.backends.signals import connection_created
        from django.db.models.signals import post_migrate

        from . import rls

        connection_created.connect(rls.on_connection_created, dispatch_uid='gestorpro_rls_connection')
        post_migrate.connect(rls.on_post_migrate, sender=self, dispatch_uid='gestorpro_rls_post_migrate')
        for command in (migrate.Command, flush.Command, makemigrations.Command, showmigrations.Command):
            rls.maintenance_command(command)
