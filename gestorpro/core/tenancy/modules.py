"""
Módulos opcionales que cada empresa enciende o apaga según su tipo de negocio.

Una lavandería no produce; una panadería sí. El Core solo guarda las claves
encendidas en `Tenant.modules` (no conoce las capacidades): cada vista de una
capacidad declara `required_module` y el permiso del Core lo exige.
Fail-closed: un módulo que no está en la lista está apagado.
"""
OPTIONAL_MODULES = {
    'production': 'Producción y recetas',
    'waste': 'Mermas',
}


def is_enabled(tenant, key: str) -> bool:
    return key in (tenant.modules or [])
