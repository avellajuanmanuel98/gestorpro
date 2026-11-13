# Documento 05 — Fase 6: catálogo de productos e ingredientes

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-10-09 |
| **Depende de** | [04 — Fase 5](04-fase-5-sistema-de-diseno.md) |

---

## 1. Modelo: un único `Item`, pantallas separadas (decisión D-6)

`Product` pasa a llamarse `Item` (migración con `RenameModel`: no se pierden datos ni las líneas de factura). El campo `kind` define qué es cada ítem:

| `kind` | Pantalla | Se vende | Existencias | Ejemplo |
|---|---|---|---|---|
| `finished_good` (Elaborado) | Productos | Siempre | Sí | Pan de bono, torta |
| `resale` (Reventa) | Productos | Siempre | Sí | Gaseosa, agua |
| `service` (Servicio) | Productos | Siempre | **No** (forzado a 0, por unidad) | Domicilio |
| `raw_material` (Ingrediente o insumo) | Ingredientes | Opcional (`is_sellable`) | Sí | Harina, huevos, bolsas |

**Por qué un solo modelo:** compras, existencias, unidades, costo y mermas funcionan igual para productos e ingredientes. Además, hay cosas que son ambas a la vez, como el queso que se usa en el pan y también se vende por libra: con un solo modelo no hay que duplicarlo.

**Conceptos separados** (condición 6 del brief):

| Concepto | Dónde vive |
|---|---|
| Producto terminado / materia prima / ingrediente | `Item.kind` |
| Unidad de medida | `UnitOfMeasure` (global) y `Item.unit` |
| Existencia | `Item.stock` (transitorio hasta la Fase 8, ver §5) |
| Costo | `Item.avg_cost`, por unidad del ítem |
| Movimientos y recetas | Fase 8 (libro de inventario y `Recipe`) |

---

## 2. Unidades de medida

`catalog.UnitOfMeasure` es **global**: igual para todas las empresas y sembrada por migración. Cada unidad tiene una **dimensión** (masa, volumen, conteo) y un **factor** respecto a la base de esa dimensión.

| Masa (base g) | Volumen (base ml) | Conteo (base und) |
|---|---|---|
| g = 1 · kg = 1000 · **lb = 500** · arroba = 12 500 | ml = 1 · l = 1000 | und = 1 · docena = 12 · ciento = 100 |

La libra es la colombiana (500 g), no la inglesa.

**La conversión vive en un solo lugar:** `kernel/units.py`, con tests.
- Solo convierte dentro de la misma dimensión: kilogramos a gramos sí, kilogramos a litros nunca. Pasar de masa a volumen exigiría una densidad por ingrediente, y no se adivina.
- Las cantidades usan Decimal con 4 decimales. Rechaza `float`.
- `cost_per()` reexpresa un costo en otra unidad sin redondear a centavos: $3.200/kg = $3,2/g. Lo usarán las recetas de la Fase 8 para costear en gramos.

---

## 3. Reglas que garantiza el backend (`catalog/services.py`)

Sin importar lo que envíe el frontend:

- Los productos (elaborado, reventa, servicio) **siempre** son vendibles y **exigen precio**.
- Un ingrediente nuevo **no se vende**, salvo que se marque. Si no se vende, precio e IVA se ignoran y quedan en 0.
- Un servicio no tiene existencias ni costo y se vende por unidad.
- La categoría debe ser del mismo tipo que el ítem: de productos o de ingredientes.
- El **código se genera** si no se indica: `PRD-0001`, `ING-0001`, `SRV-0001`. La unicidad sigue siendo por empresa.
- Un ítem que ya aparece en documentos no puede pasar de producto a ingrediente ni al revés.
- **Facturación:** un ingrediente que no se vende no puede facturarse (400).
- **Límite del plan:** `products` cuenta **solo productos**. Los ingredientes no consumen cupo.
- Hay dos restricciones en la base de datos como segunda línea de defensa: los productos siempre se venden, y un servicio no tiene existencias.

---

## 4. Costos: información sensible

Hay un permiso nuevo, `catalog.view_costs`.

| Rol | Ve costos, márgenes y valor del inventario |
|---|---|
| Propietario, Administrador, Inventario, Supervisor | Sí |
| Cajero | **No** |

- Sin el permiso, la API **no envía** `avg_cost`, `margin_pct` ni `stock_value`, ni en la lista ni en el detalle. Además, enviar un costo devuelve 403.
- El reporte de inventario devuelve los valores en `null` y la pantalla dice "No incluido en tu rol".
- La migración `catalog/0006` otorga el permiso a los roles existentes que ya gestionaban el catálogo y al Supervisor.

**Valor del inventario a costo.** Antes se calculaba como precio de venta × stock. Ahora es Σ(existencia × costo por unidad), separado en productos e ingredientes. Nunca se suman cantidades de ítems distintos, porque pueden estar en kilogramos, litros o unidades.

**Margen:** (precio sin IVA − costo) / precio. Lo calcula el servidor. El formulario muestra una vista previa mientras se escribe, pero el valor oficial es el del servidor.

---

## 5. Existencias y costo: transitorio hasta la Fase 8

Hoy la existencia y el costo se registran a mano, como valores de referencia. En la Fase 8:

- la existencia dejará de editarse a mano y se derivará del **libro de movimientos** (compras, producción, ventas, mermas, ajustes);
- el valor actual se convertirá en un movimiento de **saldo inicial**, sin perder nada;
- el costo pasará a calcularse por **promedio ponderado** con cada entrada, y su registro manual quedará bloqueado.

Ya se auditan como eventos propios los cambios de precio, de IVA y **de costo** (`catalog.item.cost_changed`).

---

## 6. Vertical Miga

**Al dar de alta una panadería** se crean dos grupos de categorías:
- de productos: Panes, Panes rellenos, Hojaldres, Tortas y postres, Galletería, Bebidas calientes, Bebidas frías, Lácteos y otros;
- de ingredientes: Harinas y almidones, Lácteos y huevos, Grasas, Endulzantes, Levaduras y aditivos, Rellenos y frutas, Bebidas e insumos de cafetería, Empaques.

**Catálogo base de ingredientes:** 31 ingredientes comunes de una panadería colombiana (harina de trigo, almidón de yuca, queso costeño, cuajada, arequipe, bocadillo, panela, empaques…), cada uno con su unidad y su categoría. Se crean **sin costos ni existencias**, porque cada panadería registra los suyos. La carga es idempotente: no duplica ni modifica lo que ya existe. Hay dos formas de cargarlo:

- **Desde la app:** en *Ingredientes* vacío aparece el botón "Cargar ingredientes comunes de panadería" (requiere `catalog.manage`; queda en la auditoría).
- **Por consola:** `python manage.py load_starter_catalog panaderia-la-favorita`

**Consumidor final** (Core, para todas las empresas): toda empresa nueva recibe el cliente "Consumidor final" con el documento 222222222222 que usa la DIAN. Lo necesitará el POS.

**Datos demo** (`seed_demo`, solo con DEBUG):
- 23 productos con precios, costos y existencias plausibles para 2026: pan francés, pan aliñado, almojábana, roscón de arequipe, pastel gloria, torta negra, tinto, gaseosa…
- El catálogo base de ingredientes, con costos y existencias.
- Algunos ítems quedan bajo el mínimo a propósito, para que se vean las alertas.

---

## 7. Frontend

| Pantalla | Ruta | Qué muestra |
|---|---|---|
| Productos | `/inventory` | Tipo (elaborado/reventa/servicio), precio por unidad de venta, costo y margen (con permiso), existencia con unidad |
| Ingredientes | `/ingredients` | Existencia y mínimo con su unidad, costo por unidad, valor a costo, "también se vende" |
| Reportes → Inventario | `/reports` | Valor a costo de ingredientes y de productos, valor por categoría y lista de ítems bajo el mínimo |
| Inicio | `/dashboard` | "N ítems bajo el mínimo", con la cantidad y la unidad de cada uno |

- **Formulario único (`ItemForm`) para ambas pantallas:**
  - el código es opcional;
  - el tipo se elige con tarjetas;
  - las etiquetas siguen la unidad ("Costo por kg", "Existencia actual (kg)");
  - muestra el margen en vivo.
- En la factura, el buscador ofrece **solo ítems vendibles**.

**Bug corregido.** Los `<select>` no controlados tomaban su valor al montarse. Si las categorías llegaban después, al editar un producto se mostraba "Sin categoría" en lugar de la real. Ya pasaba en el formulario anterior de productos, y en el nuevo afectaba también a la unidad. Ahora el formulario se monta cuando las opciones están cargadas. Se verificó en el navegador: al editar, la unidad y la categoría son las correctas.

---

## 8. Tests

- **Backend: `tests/core/test_catalog.py`** (23 tests):
  - conversión y rechazo entre dimensiones;
  - reglas por tipo, código automático, categoría del tipo correcto;
  - el cajero no ve costos, y sin permiso de costos no se pueden registrar;
  - valor del inventario a costo y oculto sin permiso;
  - un ingrediente que no se vende no se factura;
  - límite del plan solo para productos;
  - alta de panadería (categorías y consumidor final);
  - catálogo base idempotente y sin costos, por consola y por API, solo para panaderías.
- **Frontend: `lib/catalog.test.ts`**: formato de cantidades con unidad, costo unitario con decimales y vista previa del margen.

---

## 9. Pendiente

- Libro de movimientos, saldo inicial y costo promedio ponderado automático (Fase 8).
- Recetas con conversión de unidades y costo en vivo (Fase 8).
- Unidades de compra por ítem (por ejemplo, "bulto de harina = 50 kg"). Hoy se registra en la unidad base.
- Imagen de producto en el formulario (el modelo ya la soporta; llegará con la grilla del POS en la Fase 7).
