# Documento 06 — Fase 7: punto de venta (POS) y caja

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-10-10 |
| **Depende de** | [05 — Fase 6](05-fase-6-catalogo.md) |

---

## 1. Módulos nuevos (Core)

| Módulo | Modelos | Para qué |
|---|---|---|
| `core/numbering` | `Sequence` | Consecutivos por empresa, sucursal y tipo de documento, sin colisiones ni huecos |
| `core/cash` | `CashRegister`, `CashSession`, `CashMovement` | Cajas, turnos y todo lo que entra o sale del cajón |
| `core/sales` | `PaymentMethod`, `Sale`, `SaleLine`, `Payment` | Ventas de mostrador y sus pagos |

Son del Core porque cualquier comercio de mostrador los necesita, no solo las panaderías.

---

## 2. Reglas de la venta (`sales/services.py`)

Todo se valida en el backend, sin importar lo que envíe el navegador:

- **Precio, IVA y costo salen del catálogo** al momento de vender. El POS no acepta precios del cliente: si los envía, se ignoran.
- Solo se venden ítems **activos y vendibles**. Lo que se vende por unidad exige cantidades enteras; por peso o volumen se admiten decimales (0,25 kg de queso).
- **Turno de caja obligatorio:** sin turno abierto de quien vende, no hay venta.
- **Descuentos:** exigen el permiso `sales.discount` y no pueden superar el total.
- **Pagos:**
  - deben cubrir el total exacto;
  - solo el **efectivo** puede superar el total, y el servidor calcula el cambio;
  - tarjeta o transferencia por encima del total se rechaza;
  - se admiten pagos mixtos (por ejemplo, Nequi más efectivo).
- **Una sola transacción:** consecutivo, venta, líneas, pagos, movimiento de caja, existencias y auditoría se guardan juntos o no se guarda nada. Si una venta falla, **no consume número**.
- **Idempotencia:** cada intento de cobro lleva un identificador (`client_uuid`). Un doble clic o un reintento por mala señal devuelve la misma venta en lugar de duplicarla.
- **Snapshots:** la línea guarda nombre, precio, IVA y **costo** del momento. Si después cambian, la venta no cambia. Con eso se calcula el margen real de cada venta.
- **Número consecutivo** por sucursal: `V000001`, `V000002`…, con bloqueo de fila (`SELECT … FOR UPDATE`).

### Anulación

- Exige el permiso `sales.void` y un motivo.
- Solo se puede anular **mientras el turno de caja de la venta siga abierto**. Después del cierre, la corrección será una devolución, que se construirá en una fase posterior.
- Devuelve el efectivo (movimiento negativo en la caja) y las existencias. La venta **nunca se borra**: queda como "Anulada", con quién, cuándo y por qué.

### Existencias (transitorio hasta la Fase 8)

La venta descuenta `Item.stock` y la anulación lo repone. Se permite quedar en negativo, porque en panadería se vende antes de registrar la producción. En la Fase 8, cada línea de venta se convertirá en un movimiento del libro de inventario.

---

## 3. Caja (`cash/services.py`)

- **Un turno abierto por caja y uno por persona**, garantizado también con restricciones en la base de datos.
- **Movimientos con signo:** ventas en efectivo (+), anulaciones (−), ingresos (+), gastos (−) y retiros (−). Ingresos, gastos y retiros exigen motivo, y no se puede sacar más efectivo del que debería haber.
- **Inmutables:** los movimientos no se editan ni se borran. Una corrección es un movimiento nuevo.
- **Esperado = base inicial + Σ movimientos.** Solo el efectivo pasa por el cajón; tarjeta y billeteras digitales se muestran aparte para conciliarlas.
- **Cierre:**
  - se cuenta por denominación (billetes y monedas de Colombia), y el total debe coincidir con el conteo;
  - si hay diferencia, explicarla es **obligatorio**;
  - si la diferencia supera `CASH_DIFFERENCE_TOLERANCE` (por defecto $5.000), debe cerrar un supervisor (`cash.manage`);
  - el cierre queda auditado con lo esperado, lo contado y la diferencia.
- Sin `cash.manage`, cada persona solo ve y opera sus propios turnos.

---

## 4. Permisos nuevos

| Permiso | Propietario | Admin | Supervisor | Cajero |
|---|---|---|---|---|
| `sales.sell` — vender en el POS | ✓ | ✓ | ✓ | ✓ |
| `sales.view` — ver sus ventas | ✓ | ✓ | ✓ | ✓ |
| `sales.view_all` — ver las de todos | ✓ | ✓ | ✓ | — |
| `sales.discount` — descuentos | ✓ | ✓ | ✓ | — |
| `sales.void` — anular | ✓ | ✓ | ✓ | — |
| `cash.operate` — operar su caja | ✓ | ✓ | ✓ | ✓ |
| `cash.manage` — cajas de otros y diferencias grandes | ✓ | ✓ | ✓ | — |

La migración `sales/0002` prepara las empresas existentes:
- les da los medios de pago por defecto (Efectivo, Tarjeta, Nequi, Daviplata, Transferencia) y una "Caja principal" por sucursal;
- otorga estos permisos a sus roles de sistema.

Las empresas nuevas los reciben al crearse.

---

## 5. Frontend

| Pantalla | Ruta | Qué hace |
|---|---|---|
| **Vender** | `/pos` | Grilla táctil por categoría (objetivos ≥ 44 px), búsqueda con F2, Enter agrega por código (sirve con lector de barras), carrito con cantidades, cliente opcional (por defecto "Consumidor final") |
| Cobrar | (ventana) | Medios de pago, billetes sugeridos, cambio calculado, pagos mixtos, descuento si hay permiso |
| Venta registrada | (ventana) | Cambio en grande, ticket de 80 mm imprimible y "Nueva venta" con el foco puesto |
| **Caja** | `/cash` | Turno actual (base, ventas en efectivo, ingresos, salidas, lo que debería haber), ventas por medio de pago, movimientos, ingreso/gasto/retiro, cierre con conteo por denominación; historial de turnos |
| **Ventas** | `/sales` | Historial por fecha y estado, detalle, reimpresión del ticket y anulación con motivo |
| Inicio | `/dashboard` | Indicador "Ventas de hoy" (total, número de ventas, ticket promedio), con datos reales |

- El **cajero entra directo al POS** después del login.
- En el POS, el menú lateral se oculta hasta pantallas anchas, para darle todo el espacio al mostrador.
- El ticket dice **"Comprobante de venta. No es factura electrónica"**.

---

## 6. DIAN

`Sale.fiscal_status` queda en "no reportada". El modelo ya tiene numeración por sucursal y prefijo (`Sequence`) para incorporar la **resolución de numeración** y el **documento equivalente electrónico POS** en su fase propia. Esa fase requiere un proveedor tecnológico autorizado y **validación con un contador** (condición 21: no improvisar).

---

## 7. Tests

- **`tests/core/test_pos.py`** (25 tests):
  - totales e impuestos calculados en el servidor;
  - precios del cliente ignorados;
  - pagos, cambio y pagos mixtos;
  - cantidades enteras o decimales según la unidad;
  - ítems no vendibles;
  - permiso de descuento;
  - idempotencia;
  - consecutivos sin huecos;
  - snapshot de costo;
  - existencias y caja;
  - anulación (permiso, motivo, reversión y caja cerrada);
  - visibilidad por cajero;
  - un turno por caja y por persona;
  - movimientos (motivo, sobregiro e inmutabilidad);
  - cierre (diferencia, explicación, supervisor y denominaciones);
  - resumen del día;
  - configuración inicial.
- **`tests/isolation/test_pos_isolation.py`** (4 tests, obligatorios en CI): ninguna caja, venta, ítem ni medio de pago de otra empresa se ve, se usa ni se modifica.
- **Frontend: `lib/pos.test.ts`**: la vista previa del carrito calcula igual que el servidor (mismo ejemplo), sin errores de float.

---

## 8. Pendiente

- Devoluciones después del cierre de caja.
- Modo sin conexión del POS (riesgo R4; fase explícita posterior).
- Configuración de cajas y medios de pago desde la interfaz (hoy: por defecto y por el admin).
- Impresión directa a impresora térmica sin el diálogo del navegador (requiere un agente local).
- Libro de inventario: las ventas pasarán a ser movimientos (Fase 8).
