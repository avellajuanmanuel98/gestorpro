# Documento 10 — Módulos según el tipo de negocio

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-10-12 |
| **Motivo** | Una empresa que no es panadería (por ejemplo, una lavandería) veía Producción, Recetas y Mermas, y textos de panadería ("lo que sale del horno") |

## Qué cambió

**Módulos opcionales por empresa.** `Tenant.modules` guarda la lista de módulos encendidos (`core/tenancy/modules.py`):

| Módulo | Incluye | Panadería (Miga) | Otros negocios |
|---|---|---|---|
| `production` | Producción, Recetas, producción sugerida y la opción "se prepara al venderlo" en productos | Encendido | Apagado |
| `waste` | Mermas y su reporte | Encendido | Apagado |

- **Quién los enciende:** el vertical, al dar de alta la empresa (`VerticalDefinition.modules`). El dueño o un administrador (`tenant.manage`) puede cambiarlos en **Configuración → Empresa → Módulos de tu negocio**, por ejemplo un restaurante que sí produce.
- **El servidor también los exige.** Cada vista de una capacidad declara `required_module`, y `HasTenantPermission` responde 403 `module_disabled` si el módulo está apagado. Ocultarlo en el menú no basta.
- **Apagar no borra nada.** Los datos se conservan y vuelven a verse al encenderlo.
- **Migración de empresas existentes.** Se encendieron los módulos en las panaderías y en cualquier empresa que ya tuviera recetas, lotes o mermas, para que nadie pierda acceso a lo que ya usaba. Las migraciones de datos viven en cada capacidad (`production/0002`, `waste/0003`), así el Core no depende de ellas.

**Frontend:**
- El menú, las rutas (`RequireModule`), las pestañas de Reportes y el indicador de mermas en Inicio respetan los módulos.
- Los textos se adaptan al tipo de negocio con `lib/vocabulary.ts`. Una panadería habla de "ingredientes" y del "horno"; el resto, de "insumos" y "lo que produces".

## Ejemplos según el negocio

Todos los textos de ejemplo que dependen del tipo de negocio viven en `frontend/src/lib/vocabulary.ts`. Las pantallas no los escriben directamente. Una panadería ve, por ejemplo:
- en los campos: "Pan de bono", "Harina de trigo", "Panadero, cajera…", "tanda de las 6 a. m.";
- en el tipo de producto: "panes, tortas, bebidas preparadas".

El resto de negocios ve ejemplos generales ("Nombre del producto", "Lo compras listo y lo vendes tal cual", "Ej.: Vendedor, cajera…").

Los motivos de merma también dependen del negocio: "Quemado o mal horneado" solo existe en panaderías (`VerticalDefinition.waste_reasons`). En las demás empresas se desactivó si nunca se usó.

## Tests

**`tests/core/test_tenant_modules.py`** (5 tests):
- una lavandería arranca sin los módulos y una panadería con ambos;
- con el módulo apagado, el servidor responde 403 en todos los endpoints;
- encender y apagar desde Empresa, rechazando claves desconocidas;
- solo `tenant.manage` puede cambiarlos;
- la producción sugerida también respeta el módulo.

Los tests existentes crean empresas con ambos módulos encendidos (`tests/support.make_tenant`), para no depender del tipo de negocio.
