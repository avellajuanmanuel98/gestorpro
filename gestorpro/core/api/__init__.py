"""
Bases de API para recursos de empresa.

Cualquier endpoint de negocio debe construirse sobre estas clases:
- el queryset sale SIEMPRE del manager con filtro de tenant (fail-closed);
- las FKs entrantes se resuelven dentro del tenant activo;
- la unicidad se valida por tenant;
- cada método HTTP exige un permiso declarado (o se deniega).
"""
