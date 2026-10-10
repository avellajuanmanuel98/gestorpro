# Documento 08 — Fase 9: reportes y analítica

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-10-10 |
| **Depende de** | [07 — Fase 8](07-fase-8-inventario.md) |

---

## 1. Principio: ninguna cifra inventada (condición 15)

Todo número sale de los datos registrados: ventas del POS, libro de inventario y sesiones de caja.

- **Sin base de comparación no hay porcentaje.** Si el período comparable fue 0 o no existe, la variación es `null` y la pantalla dice "Sin base para comparar".
- **La producción sugerida exige historia.** Con menos de 2 semanas de datos dice que faltan datos; no propone cantidades.
- **La matriz de rentabilidad exige datos.** Solo clasifica cuando hay al menos 4 productos vendidos con costo registrado.
- **Los costos y la utilidad exigen permiso.** Se calculan y se envían solo con `catalog.view_costs`. Sin ese permiso, la respuesta **no trae** esos campos: no basta con ocultarlos en pantalla.

---

## 2. Definiciones

| Métrica | Fórmula |
|---|---|
| Ventas | Σ total cobrado de ventas completadas (con IVA, después de descuentos) |
| Ingreso sin IVA | Σ (total − IVA) |
| Costo de ventas | Σ costo congelado en cada línea al vender (promedio ponderado del momento) |
| Utilidad bruta | Ingreso sin IVA − costo de ventas |
| Margen bruto % | Utilidad bruta ÷ ingreso sin IVA |
| Ticket promedio | Ventas ÷ número de ventas |
| Mermas | Costo de los movimientos de merma, al costo del momento |
| Mermas % del costo | Mermas ÷ (costo de ventas + mermas) |
| Tasa de merma de un producto | Unidades perdidas ÷ unidades producidas en el período |
| Días de cobertura | Existencia ÷ consumo diario promedio de los últimos 30 días (consumo en producción, ventas de bebidas preparadas y mermas) |

**Anulaciones:** las ventas anuladas no cuentan, y su costo vuelve al inventario con la anulación (Fase 8).

---

## 3. Períodos comparables

Todos los reportes reciben `?period=` y se comparan contra un período equivalente anterior. Las fechas se calculan en la **zona horaria de la empresa**.

| Período | Se compara con |
|---|---|
| `today` | El **mismo día de la semana pasada**. Un sábado se compara con sábado, no con viernes. |
| `yesterday` | El mismo día de la semana anterior |
| `7d`, `30d` | Los 7 o 30 días inmediatamente anteriores |
| `this_month` | Los mismos días del mes pasado (1–10 oct contra 1–10 sep) |
| `last_month` | El mes anterior a ese |
| `this_year` | El mismo tramo del año pasado |
| `custom` (`from`, `to`) | El período anterior de igual duración (máximo 2 años) |

Las ventas por hora de un período de varios días se muestran como **promedio por día**, para que sean comparables con un solo día.

---

## 4. Endpoints

Requieren `reports.view`, salvo donde se indica otro permiso.

| Endpoint | Contenido | Permiso |
|---|---|---|
| `GET /api/analytics/summary/` | KPIs con valor, valor del comparable y variación %; bloque "requiere atención" (bajo el mínimo, existencia negativa, cajas abiertas hace más de 12 h) | `reports.view` |
| `GET /api/analytics/hourly/` | Ventas por hora, actuales y del comparable | `reports.view` |
| `GET /api/analytics/breakdown/?by=` | Ventas por `day`, `weekday`, `method`, `cashier` o `category` | `reports.view` |
| `GET /api/analytics/products/` | Por producto: vendido, ingreso, costo, utilidad, margen, producido, merma, tasa de merma y cuadrante | `reports.view` |
| `GET /api/analytics/cash/` | Aperturas y cierres con diferencias, y resumen por cajero | `cash.manage` |
| `GET /api/analytics/coverage/` | Días de cobertura de los ingredientes | `inventory.view` |
| `GET /api/waste/summary/` | Mermas por motivo y por ítem | `waste.view` |
| `GET /api/bakery/production-suggestion/?date=` | Producción sugerida, solo Miga (404 en otros verticales) | `production.view` |

Todos aceptan `?location=` para filtrar por sucursal. Una sucursal de otra empresa responde 400.

---

## 5. Exportación CSV

`breakdown`, `products` y `cash` aceptan `?export=csv`. El archivo usa los **mismos filtros y permisos** que la pantalla: sin permiso de costos, el CSV no trae columnas de costo.

**Formato pensado para Excel en español (Colombia):**
- separador `;`;
- coma decimal;
- BOM UTF-8, para que tildes y eñes se vean bien.

**Protección contra inyección de fórmulas:** un texto que empiece por `=`, `+`, `-`, `@`, tabulador o retorno de carro se antepone con `'`. Por ejemplo, el nombre de un producto `=HYPERLINK(...)` no se ejecuta al abrir el archivo.

---

## 6. Matriz volumen × margen (ingeniería de menú)

Cada producto vendido con costo se ubica frente a dos medianas: la de **unidades vendidas** y la de **utilidad por unidad**.

| | Menos vendido | Más vendido |
|---|---|---|
| **Más utilidad por unidad** | Enigma: promociónalo o cámbialo de lugar | **Estrella**: cuídalo y destácalo |
| **Menos utilidad por unidad** | Perro: reformúlalo o retíralo | Caballo de batalla: revisa costo o precio |

Se usan medianas, y no promedios, para que un producto muy caro no desplace a todos los demás.

---

## 7. Producción sugerida (exclusiva de Miga)

Para el día objetivo (por defecto mañana) se toman las **últimas 4 semanas del mismo día de la semana**.

```
promedio vendido = Σ unidades vendidas ese día ÷ semanas con la panadería abierta
sugerido         = promedio vendido − existencia actual (nunca negativo)
                   → redondeado hacia arriba a tandas completas de la receta activa
```

**Reglas:**
- Una semana cuenta solo si ese día hubo ventas. Un lunes cerrado no baja el promedio.
- Se necesitan al menos 2 semanas con datos. Si no, se dice "aún no hay suficiente historia".
- Se muestra también la merma promedio de ese día, para que el panadero decida si producir menos.
- El botón **Producir** llena el formulario de producción con la receta y la cantidad sugerida. Siempre se puede corregir antes de registrar.

**Limitación conocida:** redondear a tandas completas puede sugerir de más cuando la receta rinde mucho más de lo que se vende. Por ejemplo, una receta de 60 panes para un producto que vende 7 al día da 1 tanda de 60. La pantalla muestra el promedio y la tanda, para que la decisión sea informada.

---

## 8. Frontend

### Inicio

- **Selector de período:** hoy, ayer, 7 días, 30 días, este mes y mes pasado. Indica contra qué se compara.
- **Indicadores:** ventas, transacciones y ticket promedio, cada uno con su variación. Con permiso de costos, también utilidad bruta (con margen) y mermas, donde subir se marca en rojo.
- **Ventas por hora:** barras del período y línea punteada del comparable.
- **Requiere atención:** datos del servidor (existencias y cajas) más las facturas vencidas y la cartera por cobrar.
- **Listas de productos:** "Más vendidos" y "Los que más dejan", este último con su cuadrante.
- **Caja:** cajas abiertas y cierres con diferencia.

### Reportes

Pestañas en la URL (`?tab=`), con período compartido:

| Pestaña | Contenido |
|---|---|
| Ventas | KPIs y ventas por día, día de la semana, medio de pago, cajero o categoría, con gráfico, tabla y CSV |
| Rentabilidad | KPIs de costo; matriz volumen × margen (filtra la tabla al tocar un cuadrante); tabla por producto y CSV |
| Producción y mermas | Producido, vendido y perdido, con barra de tasa de merma; mermas por motivo y lo que más se pierde |
| Inventario | Lo anterior más los días de cobertura |
| Caja | Diferencias por cajero; aperturas y cierres; CSV |
| Facturación y Equipo | Sin cambios |

### Producción

Se agrega la tarjeta **Producción sugerida** para hoy o mañana: historial de las últimas semanas, promedio, merma, existencia, sugerido en tandas y botón **Producir**.

---

## 9. Tests

- **`tests/core/test_analytics.py`** (16 tests):
  - períodos comparables, incluido el mismo día de la semana pasada;
  - variación nula sin base;
  - KPIs y utilidad;
  - campos de costo ausentes sin permiso, y el cajero sin acceso;
  - ventas anuladas excluidas;
  - ventas por hora, día de la semana, medio de pago y cajero;
  - rentabilidad, tasa de merma y cuadrantes;
  - reporte de caja;
  - días de cobertura;
  - "requiere atención";
  - formato e inyección en CSV;
  - producción sugerida: mismo día de la semana, días cerrados, tandas, falta de historia y 404 fuera de Miga.
- **`tests/isolation/test_analytics_isolation.py`** (4 tests, obligatorios en CI):
  - ningún KPI, desglose, producto, caja, cobertura, merma, sugerencia ni CSV de una empresa incluye datos de otra;
  - filtrar por una sucursal ajena responde 400;
  - control: los datos de la otra empresa sí existen y se reportan en ella.

---

## 10. Pendiente

- Tablero consolidado por sucursal para empresas con varias sedes. Los endpoints ya filtran por `location`; falta el selector en pantalla.
- Ajustar la producción sugerida por festivos y pedidos especiales.
- Rotación de inventario por ítem y valorización histórica del inventario a una fecha.
- Reportes fiscales, que dependen de la facturación electrónica DIAN (fase posterior, con contador).
