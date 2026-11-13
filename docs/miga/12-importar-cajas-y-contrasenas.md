# Documento 12 — Importar desde Excel, cajas y pagos, y contraseñas

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-10-12 |
| **Motivo** | Lo que faltaba para arrancar en La Favorita (guía de implementación, sección 11) |

---

## 1. Importar productos e ingredientes desde Excel

**Dónde:** Productos o Ingredientes → **Importar desde Excel**. Exige el permiso `catalog.manage`.

1. **Plantilla:** se descarga en `.xlsx`, con una hoja de instrucciones y ejemplos según el tipo de negocio.
2. **Archivo:** acepta `.xlsx` o `.csv` (separado por `;` o `,`, en UTF-8 o Windows-1252), hasta 2 MB y 2.000 filas.
3. **Números en formato colombiano:** "1.500" = mil quinientos, "2,5" = dos y medio, "$ 1.234.567" y "19%" también se entienden.
4. **Vista previa:** no guarda nada. Muestra cada fila como **Nuevo**, **Ya existe** o **Revisar**, con el motivo.
5. **Confirmar:** crea las filas nuevas y válidas en **una sola transacción**: si algo falla, no se crea ninguna.

**Reglas:**
- **Mismas validaciones que el formulario:** cada fila pasa por el mismo serializer y por `services.normalize`, con los mismos permisos de costos y el **límite de productos del plan**, que se revisa para el archivo completo.
- **Solo agrega, nunca modifica:** si un ítem ya existe (mismo nombre o código), se omite. Reimportar el mismo archivo no duplica nada.
- **Categorías:** las que no existen se crean.
- **Existencia inicial:** entra como **saldo inicial** en el libro de inventario, al costo indicado.
- **Sin permiso de costos:** la columna de costo se ignora, y se avisa.
- **Precio:** va **sin IVA**, igual que en el formulario.

**Endpoint:** `GET/POST /api/catalog/import/?group=products|ingredients[&confirm=1]`. Código en `core/catalog/importer.py`. Dependencia nueva: `openpyxl`.

---

## 2. Cajas y medios de pago (Configuración → Caja y pagos)

Requiere `tenant.manage` (propietario y administrador).

**Cajas:**
- crear, renombrar y cambiar de sucursal;
- activar o desactivar; **una caja con turno abierto no se desactiva**;
- una caja inactiva desaparece de la pantalla de Caja y no admite turnos.

**Medios de pago:**
- crear (por ejemplo "Bold", tipo tarjeta), renombrar, cambiar el tipo y activar o desactivar;
- debe quedar **al menos uno activo**;
- el **Efectivo** del sistema no cambia de tipo, porque es el único que da cambio y mueve el cajón;
- un medio inactivo deja de aparecer al cobrar, y el servidor lo rechaza si alguien lo envía.

Todos los cambios quedan en la auditoría.

---

## 3. Contraseñas: recuperar y restablecer

La persona **siempre** escribe su contraseña nueva con un **enlace de un solo uso, válido 24 horas**. Nadie más la ve ni la elige.

| Cómo llega el enlace | Quién | Cuándo sirve |
|---|---|---|
| **"¿Olvidaste tu contraseña?"** en el inicio de sesión | La propia persona | Cuando la instalación tiene correo configurado (`EMAIL_HOST`). Sin correo, la pantalla explica a quién pedirle el enlace |
| **Usuarios → Contraseña** | Propietario o administrador (`access.manage_users`) | Personas de su empresa; ideal sin correo, como en la edición local |
| **Consola de plataforma → empresa → Contraseña** | Soporte de GestorPro | Cuando la empresa no puede ayudar, por ejemplo con el dueño |
| `local\restablecer-contrasena.bat` | Quien opera el computador de la edición local | Si nadie puede entrar |

**Protecciones:**
- **No revela cuentas:** "¿Olvidaste tu contraseña?" responde igual exista o no el correo.
- **Sin escalada:** el enlace que da una empresa no sirve:
  - para uno mismo;
  - para un **propietario**, si quien lo pide no es propietario;
  - para el **equipo de GestorPro**;
  - para alguien que **también usa otra empresa**: un administrador de la empresa A no puede entrar a la cuenta que esa persona tiene en la B.
- **Un solo uso:** el enlace se invalida al usarlo o al iniciar sesión.
- **Cierra sesiones:** al cambiar la contraseña, se cierran las sesiones abiertas de esa persona.
- **Queda registrado:** en la auditoría de la empresa y en los eventos de seguridad (solicitud, enlace generado y restablecimiento); desde la consola, también en la bitácora de plataforma.

**Correo:** variables `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` y `DEFAULT_FROM_EMAIL`. En desarrollo, sin servidor de correo, los correos se imprimen en la consola.

**¿El correo del dueño debe ser real?** No hace falta para entrar, porque las invitaciones y los enlaces se entregan a mano. Sí hace falta para recuperar la contraseña **por correo** cuando la instalación tenga correo configurado.

---

## 4. Tests

| Archivo | Tests | Qué cubre |
|---|---|---|
| `tests/core/test_pos_config.py` | 5 | Cajas y medios de pago, sus reglas y permisos |
| `tests/core/test_catalog_import.py` | 7 | Números colombianos, vista previa sin guardar, creación con saldo inicial, no duplicar, ingredientes, costos sin permiso, límite del plan, plantilla y permisos |
| `tests/core/test_password_reset.py` | 6 | Enlace de un solo uso que cierra sesiones, protecciones contra la toma de cuentas, correo sin revelar cuentas, sin correo configurado, soporte de plataforma, enlace alterado |
| `tests/isolation/test_reset_link_isolation.py` | 1 | Un administrador no genera enlaces para otra empresa (obligatorio en CI) |
