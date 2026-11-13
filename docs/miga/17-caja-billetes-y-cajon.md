# Documento 17 — Cobro con billetes, salidas de efectivo y cajón monedero

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-11-13 |
| **Origen** | Reunión con la familia dueña de La Favorita |

## Qué se pidió y qué se hizo

| Pedido | Qué hace GestorPro ahora |
|---|---|
| **Notas cuando se saca efectivo** (pago a un proveedor, una compra) | Ya existían **Ingreso**, **Gasto** y **Retiro** en Caja, con motivo obligatorio. Ahora hay **motivos de un toque** (Pago a proveedor, Compra de insumos, Domicilio, Servicios; en Retiro: Consignación al banco, Caja fuerte, Retiro personal) que se pueden completar ("Pago a proveedor: harina"). El botón se llama **Gasto o pago**. Al **cerrar la caja** se ve la lista del efectivo que salió en el turno, con hora, quién y motivo. |
| **Mostrar todos los billetes al cobrar** | Al cobrar en efectivo aparecen **todos** los billetes ($100.000, $50.000, $20.000, $10.000, $5.000, $2.000 y $1.000) y **Exacto**. Los billetes **se suman**: si el cliente paga con $50.000 + $20.000, se tocan los dos. El primer toque reemplaza el total propuesto. El **cambio a entregar** se ve en grande. |
| **Que se abra el cajón al cobrar** | **Ticket al cobrar: automático** (menú *Pantalla e impresora*, por computador): al confirmar el pago se imprime el ticket sin pedir clic. Con el cajón conectado a la impresora y el driver configurado (abajo), **cobrar abre el cajón**. Además, **Abrir cajón** (en Vender y en Caja) imprime un ticket corto, con fecha y usuario, que abre el cajón sin vender. |

## Instalación del cajón (una vez, en el computador de la caja)

El cajón **no se conecta al computador**: va con un cable tipo teléfono (RJ11/RJ12) al puerto **DK** o **Cash drawer** de la impresora de tickets. La impresora lo abre al imprimir, si su driver lo tiene activado. Una página web no puede mandarle la señal directa.

1. **Cable:** el cajón conectado al puerto DK de la impresora.
2. **Driver de la impresora** (Windows → Configuración → Impresoras y escáneres → la impresora térmica → **Preferencias de impresión** o **Propiedades de impresora**). Buscar la opción del cajón; el nombre cambia según la marca:
   - Epson (TM-T20, TM-T88): *Configuración del documento* → **Cash Drawer: Open before printing**.
   - Xprinter, Digital POS, 3nStar y genéricas: *Device Settings* o *Cajón* → **Open cash drawer / Abrir cajón antes de imprimir**.
   - Dejar la impresora como **predeterminada**.
3. **Chrome que imprime sin preguntar.** Crear un acceso directo en el escritorio (clic derecho → Nuevo → Acceso directo) con:
   ```
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --kiosk-printing --user-data-dir="C:\GestorPro\chrome" --app=https://gestorpro-rxy5.onrender.com
   ```
   Nombrarlo **GestorPro**. El perfil propio (`--user-data-dir`) hace que la opción funcione aunque haya otro Chrome abierto, y no se mezcla con el Chrome personal. `--kiosk-printing` imprime en la impresora predeterminada (o la última usada en ese perfil), sin el cuadro de impresión.
4. **En GestorPro** (abierto desde ese acceso directo): menú **Pantalla e impresora** → **Ticket al cobrar: automático**.
5. **Probar:** botón **Abrir cajón**; luego una venta de prueba.

**Si imprime pero no abre:** revisar el cable (puerto DK) y la opción del driver. **Si sale el cuadro de impresión:** cerrar todas las ventanas de ese acceso directo y volver a abrirlo; la opción se lee al arrancar.

## Archivos

- `frontend/src/components/pos/PaymentModal.tsx`: billetes que se suman, Exacto, Borrar.
- `frontend/src/lib/pos.ts`: `CASH_BILLS` y `receivedAfterBill` (con tests en `pos.test.ts`).
- `frontend/src/pages/cash/CashPage.tsx`: motivos de un toque, salidas en el cierre, Abrir cajón.
- `frontend/src/lib/cashDrawer.ts`: ticket corto para abrir el cajón.
- `frontend/src/pages/pos/PosPage.tsx`: ticket automático al cobrar y Abrir cajón.
- `frontend/src/store/displayStore.ts` y `frontend/src/layouts/AppLayout.tsx`: preferencia *Ticket al cobrar*.
- `tests/e2e/test_sale_to_report.py`: el recorrido del día ahora cobra con billetes y paga a un proveedor con efectivo antes de cerrar la caja cuadrada.

## Pendiente

- Confirmar la **marca y modelo** de la impresora para dar el paso 2 exacto.
- Opcional: registrar en el servidor cada **apertura de cajón sin venta** (hoy queda en papel), para control.
