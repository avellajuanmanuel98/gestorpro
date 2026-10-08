"""
Catálogo de permisos.

Cada módulo declara sus permisos en `<módulo>/permissions.py` con un dict
`PERMISSIONS = {'codigo': 'Descripción'}`. El catálogo se sincroniza con la
tabla `access_permission` tras cada `migrate`, de modo que los roles (por
empresa, editables) referencian permisos que siempre existen en código.

Agregar un módulo nuevo (core, capability o vertical) = agregar su archivo
permissions.py. No hay listas centrales que editar.
"""
from importlib import import_module

from django.apps import apps


def collect_permissions() -> dict[str, tuple[str, str]]:
    """{code: (module_label, description)} de todas las apps instaladas."""
    catalog = {}
    for app_config in apps.get_app_configs():
        if not app_config.name.startswith('gestorpro.'):
            continue
        try:
            module = import_module(f'{app_config.name}.permissions')
        except ModuleNotFoundError as exc:
            if exc.name != f'{app_config.name}.permissions':
                raise
            continue
        for code, description in getattr(module, 'PERMISSIONS', {}).items():
            if code in catalog:
                raise ValueError(f'Permiso duplicado: {code}')
            catalog[code] = (app_config.label, description)
    return catalog


def sync_permissions(**kwargs):
    from .models import Permission
    catalog = collect_permissions()
    for code, (module, description) in catalog.items():
        Permission.objects.update_or_create(code=code, defaults={'module': module, 'description': description})
    Permission.objects.exclude(code__in=catalog.keys()).delete()
