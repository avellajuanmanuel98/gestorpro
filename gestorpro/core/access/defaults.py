"""
Roles de sistema que se crean con cada empresa.

Los patrones admiten comodín por módulo ('customers.*'). Las empresas pueden
crear roles adicionales; los de sistema pueden ajustarse pero no eliminarse.
OWNER no usa lista: tiene todos los permisos, incluidos los que se agreguen
en el futuro.
"""
SYSTEM_ROLES = {
    'OWNER': {'name': 'Propietario', 'grants_all': True, 'permissions': []},
    'ADMIN': {
        'name': 'Administrador',
        'permissions': [
            'tenant.*', 'access.*', 'audit.*', 'customers.*', 'suppliers.*', 'catalog.*',
            'billing.*', 'reports.*', 'hr.*', 'assistant.*', 'sales.*', 'cash.*',
        ],
    },
    'SUPERVISOR': {
        'name': 'Supervisor',
        'permissions': [
            'tenant.view', 'customers.*', 'suppliers.view', 'catalog.view', 'catalog.view_costs',
            'billing.view', 'billing.create', 'billing.update', 'billing.apply_discount',
            'reports.view', 'hr.view', 'assistant.use', 'sales.*', 'cash.*',
        ],
    },
    'CASHIER': {
        'name': 'Cajero',
        'permissions': [
            'tenant.view', 'customers.view', 'customers.create', 'catalog.view',
            'billing.view', 'billing.create', 'sales.sell', 'sales.view', 'cash.operate',
        ],
    },
    'INVENTORY': {
        'name': 'Inventario',
        'permissions': [
            'tenant.view', 'catalog.*', 'suppliers.view', 'suppliers.create', 'suppliers.update',
        ],
    },
}


def expand(patterns, catalog_codes):
    selected = set()
    for pattern in patterns:
        if pattern.endswith('.*'):
            prefix = pattern[:-1]
            selected |= {c for c in catalog_codes if c.startswith(prefix)}
        elif pattern in catalog_codes:
            selected.add(pattern)
        else:
            raise ValueError(f'Permiso inexistente en rol de sistema: {pattern}')
    return selected
