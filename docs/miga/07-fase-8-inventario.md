# Documento 07 — Fase 8: inventario, compras, recetas, producción y mermas

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-10-10 |
| **Depende de** | [06 — Fase 7](06-fase-7-pos-y-caja.md) |

---

## 1. Principio: toda variación de existencias es un movimiento

Desde esta fase, la existencia **no se edita a mano**. Cambia solo a través del libro de inventario (`core/inventory`):

| Movimiento | Quién lo genera | Signo |
|---|---|---|
| Saldo inicial | Alta de un ítem con existencia, y la migración de los datos anteriores | + |
| Compra | Compras (`core/purchasing`) | + |
| Venta / Anulación de venta | POS (`core/sales`) | − / + |
| Consumo en producción / Producción | Producción (`capabilities/production`) | − / + |
| Merma | Mermas (`capabilities/waste`) | − |
| Ajuste (sobrante o faltante) | Conteo físico | ± |

**Cada movimiento guarda:**
- ítem, sucursal, cantidad con signo (en la unidad del ítem), costo unitario y total;
- **saldo y costo promedio justo después**, para leer el kardex sin recalcular;
- el documento de origen ("Venta V000012", "Producción P000003"…), quién lo hizo y el motivo.

Los movimientos son **inmutables**: no se editan ni se borran, y una corrección es un ajuste nuevo.

**Dónde vive la existencia:**
- `StockLevel` guarda la existencia **por sucursal**;
- `Item.stock` es la suma de las sucursales;
- `Item.avg_cost` es el costo promedio de la empresa.

Los tres se actualizan **en la misma transacción** que el movimiento, con bloqueo de los ítems (`SELECT … FOR UPDATE` en orden de id, para evitar interbloqueos).

---

## 2. Costo promedio ponderado (condición 20)

Se usa el **promedio ponderado móvil**: se recalcula en cada entrada con costo.

### Entradas con costo (compra, producción, saldo inicial, devolución de venta)

```
nuevo_promedio = (existencia_actual × promedio_actual + cantidad_que_entra × costo_de_entrada)
                 ─────────────────────────────────────────────────────────────────────────────
                                  existencia_actual + cantidad_que_entra
```

- Si la existencia actual es **cero o negativa**, el nuevo promedio es directamente el costo de la entrada. Promediar contra un faltante daría un costo sin sentido.
- El resultado se redondea a 4 decimales (ROUND_HALF_UP), porque los costos por gramo necesitan decimales.

### Salidas (venta, consumo, merma, faltante)

Salen **al promedio vigente**, que queda **congelado** en el movimiento. El promedio no cambia con una salida. Así, el costo de lo vendido o perdido en una fecha no se altera aunque después cambien los precios de compra.

### Sobrante de un conteo

Entra al promedio vigente, sin cambiarlo.

### Ejemplo (verificado en el navegador con los datos demo)

| Paso | Existencia | Promedio |
|---|---|---|
| Saldo inicial: 85 kg de harina a $3.200 | 85 kg | $3.200 |
| Compra: 2 arrobas (25 kg) a $42.500 c/u → $3.400/kg | 110 kg | (85×3.200 + 25×3.400) / 110 = **$3.245,45** |
| Producción consume 3 kg | 107 kg | $3.245,45 (sale a ese costo) |

### Existencia negativa

Se permite, porque en panadería se vende antes de registrar la producción. Se ve como alerta, y la corrige la siguiente compra, la producción o un conteo físico.

---

## 3. Compras (`core/purchasing`)

- Se compra en la unidad del proveedor (bulto, arroba, libra, kg…) y el servidor **convierte** a la unidad del ítem con `kernel/units`. Kilos a litros se rechaza.
- El total lo calcula el servidor. Consecutivo por sucursal: `C000001`.
- Entra como "Compra" y actualiza el costo promedio.

---

## 4. Recetas y producción (`capabilities/production`)

### Receta

- Pertenece a un producto elaborado. Indica cuánto **rinde** y sus ingredientes, cada uno con cantidad, unidad de la misma dimensión y porcentaje de **desperdicio**.
- **Costo estimado** = Σ (cantidad convertida × (1 + desperdicio %) × costo promedio del ingrediente). El **costo unitario** es ese total dividido por el rendimiento, y el margen se calcula frente al precio de venta.
- **Versiones:** si la versión activa ya se usó en producción, guardar cambios crea la versión siguiente y desactiva la anterior. Los lotes viejos conservan su receta y su costo. Si no se ha usado, se edita en el lugar.
- **Validaciones:**
  - solo productos elaborados;
  - un ingrediente debe manejar existencias, no puede ser el mismo producto ni repetirse;
  - las unidades deben ser compatibles.

### Producción (un lote)

1. Se elige la receta y cuánto se produjo. El sistema propone lo que se debería consumir: la receta escalada, por ejemplo ×2 para 80 panes con una receta que rinde 40.
2. Se puede corregir lo **realmente usado**, por ejemplo 9 huevos en vez de 8.
3. En una transacción:
   - se descuentan los ingredientes al costo promedio;
   - entra el producto con costo = Σ consumos / cantidad producida, que se promedia con su existencia;
   - se asigna un consecutivo `P000001` y queda auditado.

### Bebidas preparadas (`consume_on_sale`)

El tinto o el café con leche no se producen por lotes: al **venderse**, el POS descuenta los ingredientes de su receta activa (café, panela, vasos…) y la línea de venta toma ese costo. El producto en sí no maneja existencias.

Para respetar las capas, el Core no conoce las recetas. La capacidad de producción registra un "resolvedor" (`inventory.set_recipe_resolver`) al arrancar. Si el producto no tiene receta activa, la venta no se bloquea y la línea queda sin costo.

---

## 5. Mermas (`capabilities/waste`)

- **Registro en pocos toques:** qué, cuánto y por qué. Motivos por defecto: sobrante del día, quemado o mal horneado, vencido, dañado o caído, degustación y consumo del personal.
- Sale del inventario al costo vigente, que queda congelado. El listado muestra cuánto dinero se perdió en el período (con permiso de costos).
- **El cajero puede registrar mermas** (por ejemplo, el pan que se cayó), pero no consultar el listado ni ver costos.

---

## 6. Conteo físico (`core/inventory`)

Se escribe lo que hay en el estante. El sistema compara con la existencia de esa sucursal y registra la diferencia como **ajuste** (sobrante o faltante), con nota y auditoría.

---

## 7. Cambios en módulos existentes

- **Catálogo:**
  - la existencia se ingresa solo al crear el ítem, como saldo inicial; después es de solo lectura, con enlace a sus movimientos;
  - el costo admite un valor de referencia **solo mientras el ítem no tiene existencias**, para costear recetas antes de la primera compra; con existencias, lo calcula el promedio ponderado.
- **POS:**
  - la venta genera movimientos de salida, y la anulación revierte **exactamente** esos movimientos, al mismo costo;
  - los ítems se bloquean al vender, así que el costo leído es el que se registra.
- **Migración `inventory/0002`:** las existencias anteriores entraron al libro como "saldo inicial" en la sucursal principal, sin perder nada.

---

## 8. Permisos nuevos

| Permiso | Propietario / Admin | Inventario | Supervisor | Cajero |
|---|---|---|---|---|
| `inventory.view` (kardex) | ✓ | ✓ | ✓ | — |
| `inventory.adjust` (conteo físico) | ✓ | ✓ | — | — |
| `purchases.view` / `purchases.create` | ✓ / ✓ | ✓ / ✓ | ✓ / — | — |
| `recipes.view` / `recipes.manage` | ✓ / ✓ | ✓ / ✓ | ✓ / — | — |
| `production.view` / `production.register` | ✓ / ✓ | ✓ / ✓ | ✓ / ✓ | — |
| `waste.view` / `waste.register` | ✓ / ✓ | ✓ / ✓ | ✓ / ✓ | — / ✓ |

Los costos (en kardex, recetas, lotes y mermas) siguen exigiendo `catalog.view_costs`. La migración `waste/0002` otorga estos permisos a los roles de sistema de las empresas existentes y crea sus motivos de merma.

---

## 9. Frontend

**Menú reorganizado:**
- **Operación:** Inicio, Vender, Caja, Ventas, Producción, Mermas.
- **Inventario:** Productos, Ingredientes, Recetas, Compras, Movimientos.
- **Gestión:** Clientes, Facturación, Proveedores, Personal, Reportes.

**Pantallas nuevas:**

| Pantalla | Qué hace |
|---|---|
| **Compras** | Registrar mercancía (proveedor, factura, ítems con unidad de compra y costo) y ver el detalle con lo que entró al inventario |
| **Recetas** | Lista con costo por unidad y margen; editor con ingredientes, unidades, desperdicio y **costo en vivo** |
| **Producción** | Elegir producto y cantidad: muestra lo que se debe consumir, la existencia (con alerta si no alcanza) y el costo estimado; permite ajustar lo realmente usado |
| **Mermas** | Formulario rápido con motivos en un toque; listado con el costo del período |
| **Movimientos** | Kardex con filtros por ítem y tipo, saldo, costo y promedio después de cada movimiento; **conteo físico** |

---

## 10. Tests

- **`tests/core/test_inventory.py`** (16 tests):
  - promedio ponderado;
  - conversión de unidades en compras;
  - costo congelado en salidas;
  - compra después de existencia negativa;
  - existencia y costo no editables;
  - inmutabilidad;
  - conteo físico (y su permiso);
  - kardex sin costos sin permiso;
  - costo de receta (conversión y desperdicio) y validaciones;
  - producción (escalado, ajuste real, costo del producto);
  - versionado de recetas;
  - venta y anulación al mismo costo;
  - bebidas preparadas;
  - mermas (unidades enteras, cajero registra pero no consulta);
  - permisos de empresas nuevas.
- **`tests/isolation/test_inventory_isolation.py`** (2 tests, obligatorios en CI): ningún documento ni movimiento de otra empresa se ve, y ninguno puede usar ítems, recetas, motivos ni sucursales ajenos.

---

## 11. Pendiente

- Anular o corregir una compra registrada; hoy se corrige con un conteo físico.
- Traslados entre sucursales; el modelo ya guarda la existencia por sucursal.
- Unidades de compra por ítem, por ejemplo "bulto de 50 kg" como unidad propia del proveedor.
- Producción sugerida según las ventas del mismo día de la semana (exclusiva de Miga, Fase 9).
- Reportes de mermas, rotación y costo de ventas en el tablero (Fase 9).
