# Documento 04 — Fase 5: sistema de diseño y unificación visual

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-10-09 |
| **Depende de** | [03 — Fase 4](03-fase-4-acceso-auditoria-planes.md) |

---

## 1. Principios

1. **Calma operativa.** Superficies planas, bordes de 1 px y una sola sombra, reservada a capas flotantes (modales, menús, avisos). Sin degradados, brillos ni efectos "glass".
2. **El color significa algo.** El primario se usa para la acción principal y la navegación activa. El acento ámbar se usa en pocos puntos de marca. Los colores semánticos indican estado: éxito, alerta, error e información.
3. **Las cifras mandan.** Todo número usa dígitos tabulares (`.num`) y los montos se alinean a la derecha. Hay **un solo** formateador de COP (`lib/money.ts`).
4. **Nada inventado.** Sin permiso no se consulta la métrica y se explica ("No incluido en tu rol"). Sin datos, el estado vacío dice qué hacer.
5. **Cada acción responde.** Aviso (toast) al guardar, error del servidor en el formulario y `ConfirmDialog` para lo destructivo, con el nombre del objeto y la consecuencia.

---

## 2. Tokens (`src/index.css`)

Los componentes **solo** usan tokens semánticos. El modo oscuro y la marca se cambian en un único lugar.

| Token (utilidad Tailwind) | Uso |
|---|---|
| `bg-canvas` | Fondo de la aplicación |
| `bg-surface` / `bg-surface-muted` | Tarjetas, tablas, modales / zonas secundarias, hover |
| `border-line` / `border-line-strong` | Bordes de superficies / bordes de controles |
| `text-ink` / `text-ink-muted` / `text-ink-subtle` | Texto principal / secundario / terciario |
| `bg-primary`, `text-primary-ink`, `bg-primary-soft` | Acción principal, enlaces y navegación activa |
| `bg-accent`, `text-accent-ink`, `bg-accent-soft` | Acento de marca (Miga) |
| `success`, `warning`, `danger`, `info` (+ `-soft`) | Estados |
| `--chart-1…5`, `--chart-grid` | Paleta de gráficos, validada en claro y oscuro |
| `shadow-overlay` | Única sombra: capas flotantes |

**Marca.** Azul tinta como primario (`#1f3b73`), sobrio y "financiero", con ámbar miel como acento (`#e9a23b`). Los verticales futuros cambian **solo el acento**.

**Tipografía.** Inter Variable alojada en la propia app (`@fontsource-variable/inter`). Sin peticiones a Google Fonts ni bloqueo de render.

**Identidad.** El componente `Brand` muestra **"Miga by GestorPro"** si la empresa es una panadería y **"GestorPro"** en el resto. El símbolo es una "M" sobre fondo tinta con una "miga" de acento, sin panes dibujados.

---

## 3. Componentes (`src/components/ui`)

| Componente | Notas |
|---|---|
| `Button` | primary · secondary · ghost · outline · danger; `loading` con `aria-busy` |
| `Input`, `Select`, `Textarea` | Etiqueta asociada (`htmlFor`/`id`), `aria-invalid`, `aria-describedby`, ayuda y error |
| `Combobox` | Búsqueda **en el servidor** con *debounce*; ARIA combobox; teclado ↑ ↓ Enter Esc |
| `DataTable` | Skeleton de carga, estado vacío, paginación del servidor, cifras a la derecha y **tarjetas en móvil** |
| `Modal` | Portal a `<body>`, foco atrapado, Escape, devuelve el foco y respeta `autoFocus` |
| `ConfirmDialog` | Reemplaza a `confirm()` en toda la app |
| `Toaster` + `toast.success/error/info` | Avisos con `aria-live` |
| `Tabs` | `role="tablist"`, flechas ← → |
| `KpiTile` | Valor + contexto real; estados de carga y "no disponible" |
| `PageHeader` + `Page` | Encabezado y contenedor de página consistentes |
| `Card`, `Badge`, `Alert`, `EmptyState`, `Pagination`, `SearchInput`, `RowActions`, `FormActions`, `Skeleton` | — |

Compartidos en `lib/`: `money` (formato COP), `dates`, `status` (estados de factura y activo/inactivo), `options` (documentos, categorías, áreas), `errors`, `charts`, `markdown`, `useDeleteDialog` y `useDebounced`.

---

## 4. Pantallas

**Todas** las pantallas pasaron al kit, con modo oscuro, tablas comunes, avisos y confirmaciones: Inicio, Clientes, Facturación (lista, nuevo documento y detalle), Productos (productos y categorías), Proveedores, Personal, Reportes, Empresa, Usuarios, Roles, Auditoría, Login, Registro, Aceptar invitación y el asistente de IA.

Novedades funcionales:

- **Inicio:** bloque **"Requiere atención"** con datos reales (facturas vencidas, productos bajo el mínimo y saldo por cobrar), con enlace a cada pantalla.
- **Detalle de factura:** líneas, totales y cambio de estado (enviada, pagada, vencida, anulada) según los permisos. Antes no se podía ni consultar una factura.
- **Nuevo documento:** cliente y productos con búsqueda (ya no hay listas limitadas a 100) y vista previa de totales; el total definitivo lo calcula el servidor.

---

## 5. Problemas encontrados y corregidos en esta fase

| Severidad | Problema | Corrección |
|---|---|---|
| **Alta (seguridad)** | **XSS almacenado en el asistente de IA.** Su respuesta, que repite datos escritos por otros usuarios (por ejemplo, nombres de clientes), se insertaba como HTML sin escapar. Daba acceso a los tokens de sesión. | `lib/markdown.ts` escapa todo el HTML antes de dar formato. Hay test de regresión con Vitest, que falla sin la corrección. |
| **Alta (datos)** | Al editar un cliente, proveedor o producto, el formulario se rellenaba con los datos del **listado**, que no trae todos los campos. Guardar **borraba** notas, dirección, descripción, tipo de documento, sitio web… | Al editar se carga primero el detalle completo. |
| **Alta (integridad)** | Las transiciones de estado de factura no se validaban: por la API, una factura pagada podía volver a borrador y una cancelada podía reactivarse. | `Invoice.ALLOWED_TRANSITIONS`; pagada y cancelada son estados finales. Con test. |
| Media | Aceptar una invitación con una contraseña débil devolvía **500**. | 400 con el motivo. Con test. |
| Media | El panel de la IA decía "Powered by Claude", pero el backend usa Groq (Llama). | Texto honesto y aviso de que la IA puede equivocarse. |
| Baja | El enlace "¿Olvidaste tu contraseña?" no hacía nada. | Retirado hasta que exista la recuperación. |
| Baja | Al abrir un formulario, el foco iba al botón de cerrar. | El modal respeta `autoFocus`. |
| Baja | Los `<select>` se veían deshabilitados (`:read-only` en CSS). | El estilo de solo lectura aplica solo a campos de texto. |

---

## 6. Alta de clientes reales: Panadería La Favorita

`onboard_tenant` da de alta un cliente real **sin datos demo** y genera la invitación del **propietario**: el enlace se muestra una sola vez y el dueño define su contraseña.

```bash
python manage.py onboard_tenant "Panadería La Favorita" <email-del-dueño> --plan business --city Bogotá
python manage.py onboard_tenant --reinvite panaderia-la-favorita <email-del-dueño>   # si el enlace se pierde o vence
```

Las capturas de esta fase usan "Panadería La Favorita" con **datos de ejemplo** creados solo en el entorno local de pruebas.

---

## 7. Pendiente

- Numeración automática de documentos (hoy el número se escribe a mano; con el POS llegarán las secuencias).
- Recuperación de contraseña por email (requiere la infraestructura de correo).
- Página interna de catálogo de componentes (`/design`) y tests de componentes.
- Revisión de accesibilidad AA completa con lector de pantalla (Fase 14).
- División del bundle (*code splitting*): el JS principal pesa unos 890 kB sin comprimir (Fase 13).
