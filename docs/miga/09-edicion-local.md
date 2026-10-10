# Documento 09 — Edición local (instalación en el negocio)

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-10-10 |
| **Motivo** | Panadería La Favorita quiere el sistema 100 % local, sin mensualidad en la nube |
| **Desplaza** | La Fase 10 (administración SaaS) pasa a después de esta |

---

## 1. Qué es

Es **el mismo GestorPro**, con el mismo código y la misma base de datos, instalado en un computador de la panadería. Ese computador hace de servidor:

- **La caja** usa GestorPro en ese mismo computador.
- **La tablet y el celular del dueño** entran por el wifi del local, con una dirección como `http://192.168.1.40:8000`.
- **No se necesita internet para vender.** Si se cae el internet, todo sigue funcionando mientras el computador y el router estén encendidos.
- **Internet solo hace falta para actualizar** a una versión nueva.

El modelo multiempresa se conserva (aquí hay una sola empresa). Así, si más adelante quieren pasarse a la nube, se lleva la copia de seguridad y listo.

---

## 2. Cómo se instala (lo haces tú, una sola vez)

### Requisitos en el computador de la panadería

1. **Windows 10 u 11.**
2. **Python 3.12 o superior**, desde python.org, marcando *"Add python.exe to PATH"*.
3. **Git**, desde git-scm.com, para descargar el código y las actualizaciones.
4. **PostgreSQL**: el zip de binarios de enterprisedb.com, descomprimido en `%USERPROFILE%\pgsql`.
5. **No necesita Node.js**: la aplicación ya viene compilada en `frontend/dist`.

### Pasos

```bat
git clone https://github.com/avellajuanmanuel98/gestorpro.git
cd gestorpro
git checkout claude/zen-johnson-hhz8hm
local\1-instalar.bat
```

> Si el repositorio es privado, ese equipo necesita acceso de solo lectura a GitHub (iniciar sesión con Git o usar un token de solo lectura); lo mismo para `actualizar.bat`.

El instalador pregunta:
- el nombre del negocio, el email del dueño, si es panadería y la ciudad;
- una carpeta para la **segunda copia de seguridad** (USB, disco externo o una carpeta de OneDrive o Google Drive);
- si GestorPro debe abrirse solo al encender el computador.

Al final muestra el **enlace de invitación**. El dueño lo abre en ese computador, con GestorPro iniciado, y define **su propia contraseña**: nadie más la conoce. El enlace también queda en `GestorPro-datos\LEEME-invitacion.txt`, y ese archivo **se borra solo** cuando la invitación se usa.

**Qué hace por debajo:**
1. Crea `%USERPROFILE%\GestorPro-datos\` con la configuración y secretos aleatorios (`gestorpro.env`).
2. Crea una base PostgreSQL **propia**:
   - puerto 5435, para no chocar con otra instalación;
   - escucha **solo en ese computador** y **exige contraseña**;
   - la aplicación entra con un usuario sin privilegios de administrador;
   - si PostgreSQL trae ICU, ordena los nombres en español.
3. Aplica las migraciones y prepara los archivos de la aplicación.
4. Crea la empresa con licencia **activa y sin vencimiento** (`set_plan --active --no-end`) y, si es panadería, carga los ingredientes comunes.
5. Hace la **primera copia de seguridad** para comprobar que las copias funcionan.
6. Opcional: deja un acceso en la carpeta de Inicio de Windows, que no requiere permisos de administrador, e intenta abrir el puerto en el firewall para redes privadas. Si no hay permisos, Windows lo preguntará la primera vez.

---

## 3. Uso diario (la panadería)

Los archivos están en la carpeta `local\` del programa.

| Archivo | Para qué |
|---|---|
| `GestorPro.bat` | Abre GestorPro. Deja la ventana **abierta** (se puede minimizar). Se abre solo si activaste el arranque automático. |
| `estado.bat` | Muestra la dirección para la tablet, cuándo fue la última copia y los avisos (sin segunda copia, poco disco…). |
| `copia-de-seguridad.bat` | Hace una copia ahora mismo. |
| `restaurar-copia.bat` | Vuelve a una copia anterior. Hay que cerrar GestorPro antes. |
| `actualizar.bat` | Instala la versión nueva (hace una copia antes). Hay que cerrar GestorPro antes. |

**Desde la tablet o el celular:** se conectan al **mismo wifi** y abren la dirección que muestra la ventana de GestorPro (o `estado.bat`), por ejemplo `http://192.168.1.40:8000`. Conviene guardarla como acceso directo en la pantalla de inicio.

> **Recomendación:** reservar en el router una IP fija para el computador de GestorPro, para que la dirección no cambie.

---

## 4. Copias de seguridad

- **Cuándo:**
  - automáticas, **cada día a las 9:00 p. m.** (`GESTORPRO_HORA_COPIA`), mientras GestorPro esté abierto;
  - al abrir GestorPro, si la última copia tiene más de 26 horas (por ejemplo, porque el computador estuvo apagado);
  - antes de cada actualización y de cada restauración.
- **Qué contiene:** un `.zip` con la base de datos (`pg_dump`) y las imágenes subidas (productos, logo). Antes de guardarla **se verifica** que se pueda leer: una copia ilegible no cuenta como copia.
- **Dónde se guarda:**
  - en `GestorPro-datos\copias\`;
  - **además**, en la carpeta extra (`GESTORPRO_COPIA_EXTRA`), si está configurada.
- **Cuántas se guardan:** las **30 más recientes** en cada carpeta. Solo se borran archivos con el nombre de las copias de GestorPro; nada más se toca.
- **Avisos en `estado.bat`:** si no hay segunda copia, si la carpeta extra no está conectada, si la última copia tiene más de 2 días o si queda poco disco.

> **La copia en el mismo disco no protege si el disco se daña o se roban el computador.** La segunda copia en un USB o en una carpeta sincronizada con la nube es parte de la instalación, no un extra.

### Restaurar (`restaurar-copia.bat`)

1. Lista las copias de ambas carpetas, de la más nueva a la más vieja.
2. Pide el número de la copia y luego escribir **RESTAURAR**.
3. Hace una copia de cómo está todo **ahora**.
4. Carga la copia elegida en una base **nueva** y, solo si todo salió bien, la pone en uso.
5. La base anterior **no se borra**: queda guardada como `gestorpro_antes_AAAAMMDD_HHMMSS`, y las imágenes anteriores como `archivos_antes_…`. `estado.bat` las lista.
6. Aplica las migraciones, por si la copia era de una versión anterior.

**Probado de punta a punta:** se hizo una copia, se creó un producto, se restauró la copia, el producto desapareció, la imagen se recuperó y la base anterior quedó guardada.

---

## 5. Seguridad

| Medida | Detalle |
|---|---|
| `DEBUG` apagado | Configuración `config/settings/local_edition.py`, tan cerrada como producción |
| Secretos aleatorios | `SECRET_KEY` de 64+ caracteres; la configuración se niega a arrancar con una clave débil |
| Sin datos demo ni superusuarios | El instalador no los crea, y un test lo vigila |
| Nunca se destruye una base | Restaurar crea una base nueva y guarda la anterior. El único `DROP` permitido es el de la base **temporal** de una restauración fallida, y un test lo verifica |
| PostgreSQL | Solo escucha en ese computador, con contraseña; la aplicación entra con un usuario sin privilegios de administrador |
| Hosts permitidos | Solo `localhost`, el nombre del equipo y sus IP de la red local (se recalculan al arrancar); cualquier otro host se rechaza (400) |
| Encabezados | `X-Frame-Options: DENY`, `nosniff` y `Referrer-Policy`, incluso en `index.html` (que sirve WhiteNoise) |

**Limitación conocida:** sin HTTPS, la contraseña viaja sin cifrar por el wifi del local. Mitigaciones:
- un wifi con contraseña WPA2 o WPA3;
- no usar una red abierta ni de invitados para la caja.

HTTPS local con certificado queda como mejora futura.

**Cambios hechos para que funcione por HTTP en la red local:**
- **Identificador de cada venta:** el navegador solo ofrece `crypto.randomUUID` con HTTPS o en `localhost`. Desde la tablet (`http://192.168.x.x`) ahora se genera con `crypto.getRandomValues`, que sí está disponible. Hay un test.
- **Copiar enlaces de invitación:** `navigator.clipboard` tampoco existe sin HTTPS. Ahora se usa el método clásico como respaldo (`lib/clipboard.ts`).
- **Avisos en la consola:** se desactivó el encabezado COOP, que el navegador ignora sin HTTPS y solo llenaba la consola de avisos.

---

## 6. Actualizar (`actualizar.bat`)

1. Exige que GestorPro esté cerrado y que nadie haya modificado archivos del programa.
2. Hace una copia de seguridad.
3. Descarga la versión nueva con `git pull --ff-only`. Sin internet no cambia nada.
4. Instala las dependencias y aplica las migraciones.

Si algo falla, la copia de antes está en `copias\`.

---

## 7. Qué hay que decidir con el cliente

- **Quién actualiza y cada cuánto.** Las mejoras y correcciones llegan solo si alguien ejecuta `actualizar.bat`.
- **Licencia y soporte.** El sistema no impone vencimiento. Es un acuerdo comercial: pago único, soporte anual o similar.
- **Respaldo de energía.** Un apagón no daña la base (PostgreSQL se recupera solo), pero un UPS pequeño evita interrupciones en la caja.

---

## 8. Archivos

| Archivo | Qué es |
|---|---|
| `scripts/local_edition.py` | Comandos instalar, iniciar, copia, restaurar, actualizar y estado. El servidor web es **waitress** (Python puro, funciona en Windows) y las copias diarias corren en un hilo dentro del mismo proceso |
| `local/*.bat` | Lanzadores para Windows |
| `config/settings/local_edition.py` | Configuración |
| `config/urls.py` | Sirve las imágenes subidas cuando `SERVE_MEDIA` está activo |
| `set_plan --no-end` | Licencia sin vencimiento |
| `tests/platform/test_local_edition.py` | 9 tests: copias diarias, rotación, listado, confirmación, secretos, hosts, configuración y licencia |
| `tests/isolation/test_deploy_safety.py` | 2 tests más: la edición local no siembra datos demo, no destruye bases y corre con `DEBUG` apagado |

---

## 9. Pendiente

- HTTPS en la red local (certificado propio) para cifrar el wifi.
- Instalador sin Git ni Python visibles (un `.exe` empaquetado), si se instala en muchos negocios.
- Aviso en la propia aplicación cuando la última copia sea vieja; hoy aparece en `estado.bat`, y las copias automáticas fallidas se avisan en la ventana de GestorPro.
- Limpieza guiada de bases `gestorpro_antes_*` antiguas.
