# Documento 16 — Modo fácil (personas mayores)

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-11-10 |
| **Para quién** | La dueña de La Favorita (67 años), que usará GestorPro en un computador |

## Qué hace

Se activa en el menú lateral, en **Pantalla**. Queda guardado **en ese computador**, no en la cuenta: lo configura una vez quien instala.

| Opción | Efecto |
|---|---|
| **Letra: Normal / Grande / Muy grande** | Escala toda la pantalla (100 %, 115 % o 130 %): textos, botones, campos y espacios crecen parejo, sin desarmar el diseño. También aplica al login. |
| **Modo fácil** | Menú corto con las 6 opciones de todos los días (Inicio, Vender, Caja, Ventas, Productos, Reportes), más grandes y sin grupos. El resto queda en **Más opciones**. |
| | Las acciones de las tablas se escriben con palabras: **Editar** y **Eliminar**, no solo íconos. |
| | Se oculta el botón flotante del asistente: una cosa menos en pantalla, y no tapa tablas. |

**Recomendado para la dueña:** modo fácil + letra **Grande**. "Muy grande" sirve en pantallas grandes; en un portátil de 1366×768, las tablas anchas se desplazan a lo ancho.

## Arreglos que salieron al probarlo

- **Las tablas cortaban lo que no cabía**, sin dejar desplazarse (`overflow-hidden`). Con letra grande, o en un portátil pequeño, la columna de acciones quedaba oculta y era inalcanzable. Ahora la tabla se desplaza a lo ancho, y la columna de acciones queda **fija a la derecha**, siempre visible.
- **Los textos con tamaño fijo en píxeles** (rótulos de grupo, marca y otros) no crecían con la letra. Ahora están en `rem`.

## Archivos

- `frontend/src/store/displayStore.ts`: preferencias de pantalla (persistidas en el navegador).
- `frontend/src/layouts/AppLayout.tsx`: menú corto, "Más opciones" y panel "Pantalla".
- `frontend/src/components/ui/RowActions.tsx`: acciones con palabras en modo fácil.
- `frontend/src/components/ui/DataTable.tsx`: desplazamiento horizontal y acciones fijas.
- `frontend/src/App.tsx`: oculta el asistente en modo fácil.
- `frontend/src/lib/display.test.ts`: 3 tests.

## Pendiente (siguientes pasos del refinamiento UX, Fase 14)

- Probarlo **con la dueña** y ajustar según lo que le cueste. Es la prueba que más enseña.
- Textos de ayuda breves en los pasos clave (abrir caja, vender, cerrar caja).
- Confirmaciones con el monto en lenguaje simple antes de acciones importantes.
