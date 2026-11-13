# Documento 13 — Fase 11: Testing

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-10-13 |
| **Alcance** | Concurrencia real, invariantes contables, E2E en navegador, cobertura obligatoria en CI |

La Fase 11 endurece la red de tests. No reemplaza los tests de cada fase anterior: busca lo que esos tests no podían ver, es decir:

- dos operaciones al mismo tiempo;
- miles de combinaciones en orden;
- la pantalla real.

---

## 1. Concurrencia real (`tests/core/test_concurrency.py`, 10 tests)

**Cómo funcionan.** Cada test lanza varios hilos contra PostgreSQL. Cada hilo tiene su propia conexión y su propia transacción. Una barrera los libera a la vez. Se usan los servicios de dominio reales, no simulaciones.

**Qué verifican.** No basta con que "no falle". El resultado debe ser el mismo que si las operaciones hubieran ocurrido una detrás de otra.

| Escenario | Qué debe cumplirse |
|---|---|
| 12 ventas simultáneas desde 3 cajas | Consecutivos V000001…V000012 sin huecos ni repetidos. Existencia exacta. Cada caja con su esperado exacto. |
| La misma venta enviada dos veces a la vez (reintento de la tablet) | Una sola venta. **El reintento recibe la venta ya creada; no se rechaza.** |
| Venta contra cierre de caja | O la venta entra y queda en el esperado del cierre, o se rechaza. Nunca queda una venta "fuera" de un turno cerrado. |
| Anular la misma venta dos veces a la vez | Se anula una vez. El efectivo y la existencia se devuelven una sola vez. |
| Dos personas abren la misma caja a la vez | Un solo turno abierto. |
| Dos retiros simultáneos que juntos superan el efectivo | Solo pasa uno; el cajón nunca queda en negativo. |
| 6 compras simultáneas del mismo ingrediente | El costo promedio se puede recalcular desde el libro, en su orden. Los consecutivos de compra quedan sin huecos. |
| Vender mientras se recibe una compra | El libro es consistente y cada venta sale al promedio vigente en su momento. |
| Conteo físico mientras se vende | El conteo se aplica sobre la existencia del momento; lo vendido después se descuenta de lo contado. |
| Dos invitaciones con el último cupo del plan | **Solo entra una.** |

### Problemas reales encontrados y corregidos

1. **Reintento simultáneo de una venta.** Si la tablet reenviaba la misma venta (mismo `client_uuid`) justo mientras se registraba la primera, el segundo envío recibía el error "Esta venta ya se está registrando". El cajero veía un error aunque la venta sí había quedado.

   Ahora, tras esperar el bloqueo del turno, el servicio vuelve a buscar la venta y devuelve la ya creada (`core/sales/services.py`, `_already_registered`).

2. **Límites del plan con altas simultáneas.** Dos invitaciones, dos productos o dos roles creados a la vez con el último cupo pasaban los dos: cada uno contaba antes de que el otro guardara.

   Ahora `entitlements.check_limit` recibe la **función** que cuenta, no el número. Antes de contar bloquea la fila de la empresa hasta el final de la transacción, así que la segunda alta espera a la primera y cuenta lo que esta ya creó. Si se llama fuera de una transacción, falla de forma explícita. Aplica a usuarios, productos (formulario, edición e importación) y roles personalizados.

Los tests usan `transaction=True, serialized_rollback=True`: el vaciado de la base entre tests no se lleva los datos que crean las migraciones (planes, unidades, permisos).

---

## 2. Invariantes contables (`tests/core/test_invariants.py`, 3 semillas)

**El día simulado.** Una simulación con semilla fija (reproducible) recorre un día de panadería con dos cajas: 220 operaciones al azar. Una corrida típica deja:

- ~90 ventas, entre efectivo, otros medios, pagos mixtos, cambio y descuentos;
- ~10 anulaciones;
- ~30 compras y ~25 producciones con receta;
- mermas, conteos físicos y bebidas que descuentan su receta;
- ingresos, gastos y retiros de caja;
- varios cierres con y sin diferencia.

También intenta operaciones que deben fallar (pagar de menos, anular algo ya anulado, retirar más efectivo del que hay…). Esas deben fallar sin dejar rastro.

**Lo que se verifica al final:**

| Área | Invariante |
|---|---|
| Inventario | Existencia = Σ libro = Σ existencias por sucursal. Saldo y costo promedio de cada movimiento recalculables repitiendo el libro. Valor = cantidad × costo. |
| Ventas | Línea: subtotal = cantidad × precio y total = subtotal + IVA. Venta: total = subtotal + IVA − descuento = Σ pagos. El precio siempre es el del catálogo. |
| Ventas ↔ inventario | Cada venta descuenta exactamente sus líneas, o la receta en las bebidas preparadas. Una anulada queda en cero neto. |
| Caja | Esperado = base + Σ movimientos. El efectivo de las ventas es el que entró al cajón; lo anulado salió. Diferencia = contado − esperado. No hay ventas después del cierre. |
| Analítica | Ventas, transacciones, ingreso sin IVA, costo y merma del tablero salen exactamente de esos datos. |

**¿La simulación detecta errores de verdad?** Se comprobó a propósito con dos fallos inyectados, y en ambos casos la simulación falló:

- una anulación que devolvía el doble de existencias;
- un cierre de caja con el esperado corrido en $1.

---

## 3. E2E en navegador (`tests/e2e/`)

**Cómo funciona.** Chromium real, controlado por Playwright, contra el backend servido por `live_server` y la SPA compilada (`frontend/dist`). Es lo mismo que se usa en producción y en la edición local.

**El recorrido crítico de un día:**

1. El cajero entra: va directo al POS y abre la caja con $100.000.
2. Vende 3 panes de bono en efectivo.
3. Cierra la caja contando 1 × $100.000 y 3 × $2.000. Cuadra exacto: esperado = contado = $106.000.
4. La dueña ve la salida "Venta V000001" en el libro de inventario, con saldo 17 (20 − 3).
5. El tablero de Inicio muestra exactamente **$ 6.000 en 1 transacción, ticket de $ 6.000**.

**Qué hace fallar el test:** cualquier error en la consola del navegador o cualquier respuesta 5xx durante el recorrido.

**Cómo se ejecuta:**

- **En local:** `pip install -r requirements-e2e.txt`, luego `playwright install chromium`, luego `pytest -m e2e`. Sin Playwright instalado, el test se omite.
- **En CI** (job **E2E en navegador**, obligatorio): compila el frontend desde el código del commit y corre con `E2E_REQUIRED=1`. Así, que falte el navegador o el build es un error, no una omisión.

---

## 4. Cobertura obligatoria en CI

`pytest-cov` mide la cobertura en cada push. Hay dos pisos:

| Alcance | Mínimo | Actual |
|---|---|---|
| Todo `gestorpro/` (sin migraciones) | 90 % | 92 % |
| Servicios críticos: ventas, caja, inventario, compras, consecutivos, límites del plan, empresas, identidad, accesos, producción, mermas, kernel (dinero y unidades) | 90 % | 92 % |

Si una de estas cifras baja del mínimo, CI queda en rojo.

---

## 5. Frontend

- **`lib/money.test.ts`:** formato de pesos, abreviatura solo desde un millón y nunca "NaN".
- **`lib/errors.test.ts`:** los mensajes que ve el usuario.

**Dos detalles corregidos:**

- Si el servidor respondía con una página de error (502 de un proxy), la pantalla mostraba "Request failed with status code 502". Ahora dice "El servidor tuvo un problema. Intenta de nuevo en un momento.".
- Una respuesta vacía mostraba un mensaje en blanco. Ahora muestra el mensaje por defecto.

---

## 6. Otro arreglo

`test_analytics.py::test_breakdowns_and_hourly` (Fase 9) dependía de la hora del reloj: fallaba si se corría entre las 7 y las 8 a. m. hora Colombia. Ahora la venta del test tiene hora fija.

---

## 7. Cómo correr todo

```bash
pytest -m isolation                        # aislamiento entre empresas
pytest --cov                               # suite completa + cobertura (mínimo 90 %)
pytest tests/core/test_concurrency.py      # concurrencia real
pytest tests/core/test_invariants.py       # simulación de un día
pytest -m e2e                              # navegador (requiere requirements-e2e.txt)
cd frontend && npm run lint && npm test && npm run build
```

## 8. Pendiente para fases siguientes

- **Fase 12 (Seguridad):**
  - Row-Level Security en PostgreSQL;
  - refresh token en cookie `httpOnly`;
  - revisión OWASP ASVS nivel 2;
  - restauración de copias probada en CI.
- **Más recorridos E2E:**
  - compra → producción → merma;
  - permisos del cajero (no ve costos);
  - edición local en Windows (requiere un runner Windows).
- **Rendimiento:** pruebas de carga del POS con muchas cajas, en la Fase 13.
