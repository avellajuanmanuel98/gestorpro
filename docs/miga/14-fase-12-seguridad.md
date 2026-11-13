# Documento 14 — Fase 12: Seguridad

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-10-13 |
| **Alcance** | Row-Level Security, cabeceras y CSP, límites de intentos, sesión en cookie httpOnly, verificación en dos pasos del personal, dependencias y revisión OWASP ASVS nivel 2 |

---

## 1. Row-Level Security en PostgreSQL

**Qué hace.** PostgreSQL mismo aplica la regla "cada empresa solo ve lo suyo". Es una red más debajo de las capas de la aplicación:

- el manager fail-closed;
- `save()` con verificación de llaves foráneas;
- los permisos.

Si algún día un error en el código se saltara esas capas (SQL crudo, una relación leída con el manager sin filtro, un `all_tenants` mal usado), la base igual no devolvería ni escribiría filas de otra empresa.

**Cómo funciona** (`gestorpro/core/tenancy/rls.py`):

- **Política en cada tabla de empresa.** Todas las tablas de un `TenantModel` (hoy 30) tienen la política `gestorpro_tenant_isolation`, para lectura y escritura (`USING` y `WITH CHECK`). Una fila es visible y escribible solo si:
  - su `tenant_id` es el de la empresa activa de la sesión de base de datos, **o**
  - el código declaró un acceso global con `rls_bypass()`.
- **Fail-closed.** Sin empresa activa ni acceso global declarado, no hay filas.
- **Rol restringido.** La aplicación consulta con el rol `gestorpro_rls`: sin login, sin superusuario, sin `BYPASSRLS`, sin `TRUNCATE` ni DDL. El dueño de las tablas y los superusuarios se saltan RLS, así que la app nunca consulta como ellos.
- **Mantenimiento.** Solo `migrate`, `flush`, `makemigrations` y `showmigrations` corren como dueño. Las copias de seguridad (`pg_dump` como dueño) siguen completas.
- **Sincronización.** Antes de cada consulta se envía a PostgreSQL la empresa activa, solo cuando cambia. PostgreSQL revierte esos valores con un `ROLLBACK` o un savepoint revertido; en ese caso se vuelven a enviar (hay un test exacto de eso).
- **Tablas nuevas.** `post_migrate` crea o actualiza las políticas de todos los modelos de empresa: un modelo nuevo queda protegido sin escribir nada. Un test de arquitectura falla si alguna tabla quedara sin política.
- **Si falta el rol.** Si el usuario de la base no puede usar el rol, `migrate` se detiene con instrucciones claras en lugar de dejar la app sin esta red (`GESTORPRO_RLS_REQUIRED`, activo por defecto).

**Accesos globales declarados.** Son explícitos y revisables, y cada uno va después de su propio control:

| Lugar | Por qué cruza empresas |
|---|---|
| `access.services.active_memberships_for` | Login y selector de empresa: las membresías de la persona en todas sus empresas |
| `access.services.find_pending_invitation` | El token de la invitación identifica la empresa |
| `identity.password_reset.link_for_member` | Pregunta si la persona usa OTRA empresa (regla anti-toma de cuentas) |
| `PlatformView` (consola) | Después de verificar `IsPlatformAdmin` |
| Admin de plataforma | Después de `has_permission` (personal con verificación en dos pasos) |

**Comprobado en una instalación real de la edición local:**

- El usuario de la app es dueño de la base, sin superusuario.
- La app consulta como `gestorpro_rls`. Sin empresa activa, `all_tenants` devuelve 0 filas.
- Con `pg_dump` y `pg_restore`, los 31 ítems vuelven completos.
- Si se quita el rol, `migrate` se niega con el mensaje de cómo arreglarlo.

**Edición local.** `GestorPro.bat`, `actualizar.bat` y `restaurar-copia.bat` crean el rol y se lo asignan al usuario de la app, también en instalaciones anteriores. No hay que hacer nada a mano.

**Producción (Railway).** Si el usuario de la base es superusuario, `migrate` crea el rol solo. Si no lo es, un administrador de PostgreSQL debe ejecutar:

```sql
CREATE ROLE gestorpro_rls NOLOGIN;
GRANT gestorpro_rls TO <usuario de la app>;
```

---

## 2. Cabeceras de seguridad y Content Security Policy

**La política (CSP).** Solo se permite código y recursos del propio GestorPro:

```
default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:;
font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self';
form-action 'self'; frame-ancestors 'none'
```

Esto significa: sin scripts en línea, sin `eval`, sin marcos de otros sitios y sin enviar formularios afuera. Si alguien lograra inyectar HTML, el navegador no ejecutaría su script ni lo dejaría enviar datos a otro lado.

**Dónde se aplica:**

- **Respuestas de Django (API y admin):** con el middleware de CSP de Django 6.
- **`index.html`** (lo sirve WhiteNoise sin pasar por los middlewares): la misma política, más `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy` y `Permissions-Policy` (sin cámara, micrófono, ubicación ni pagos).

**Otras cabeceras y cambios:**

- **API:** `Cache-Control: no-store`, para que ni el navegador ni un proxy guarden datos del negocio.
- **`/api/docs/` y `/api/schema/`:** solo en desarrollo, o con `API_DOCS_ENABLED=True`. En producción no se publica el mapa completo de la API. Esa página es la única que amplía la CSP, para cargar Swagger desde jsDelivr.

**Comprobado en navegador.** Recorrí con Chromium todas las pantallas de la dueña, la consola de plataforma y el admin con la CSP activa: **cero violaciones** y los gráficos se dibujan bien.

---

## 3. Límites de intentos

| Qué | Límite |
|---|---|
| Login, registro, contraseñas, invitaciones, código 2FA | 10/min por IP (ya existía) |
| **Bloqueo por cuenta** (nuevo) | 5 fallos para un mismo correo en 15 min, **desde cualquier IP** → ese correo queda bloqueado 15 min |
| Renovar la sesión | 30/min por IP |
| Cambiar la contraseña con sesión iniciada | 10/min por usuario |
| Resto de la API | 1.200/min por usuario; 120/min sin sesión |

**Cómo funciona el bloqueo** (`core/identity/lockout.py`):

- Se cuenta en la base (`SecurityEvent`), así que vale aunque haya varios procesos.
- Mientras dura, **la contraseña ni siquiera se verifica**.
- Aplica a cualquier correo, exista o no: no revela qué cuentas existen.
- Un login exitoso o una contraseña restablecida con enlace reinician el conteo.
- "¿Olvidaste tu contraseña?" sigue funcionando durante el bloqueo.
- Los códigos 2FA equivocados también cuentan.

**Contraseñas.** Ahora el mínimo es **12 caracteres** (OWASP ASVS 2.1.1). Aplica a contraseñas nuevas; las ya guardadas siguen sirviendo.

---

## 4. La sesión larga en una cookie httpOnly

**Antes.** El *refresh token* (7 días) vivía en `localStorage`, donde cualquier script de la página podía leerlo.

**Ahora** (`core/identity/tokens.py`):

- **El refresh token** viaja **solo** en la cookie `gp_refresh`:
  - `httpOnly`: JavaScript no la ve;
  - `SameSite=Strict`: otro sitio no la envía;
  - `Secure`, salvo en desarrollo y en la edición local por HTTP;
  - limitada a `/api/auth/`.
- **El token corto** (15 min) sigue en el cuerpo de la respuesta.
- **Rotación.** El refresh rota en cada uso y el anterior queda revocado. Un refresh enviado en el cuerpo se ignora.
- **Origen.** `/api/auth/token/refresh/` rechaza un `Origin` de otro sitio.
- **Cierre de sesión y cambio de empresa** revocan el refresh de la cookie.
- **Modo soporte.** La cookie del agente no se toca; al salir, su sesión se renueva sola.
- **Varias pestañas.** Si otra pestaña renovó al mismo tiempo, se usa su token en lugar de cerrar la sesión.

**Comprobado en navegador:**

- `document.cookie` vacío y nada de refresh en `localStorage`.
- Con un token corto inválido, la sesión se renueva sola por la cookie.
- La sesión sobrevive a recargar la página.
- Al salir, la cookie desaparece y no se puede volver.
- Entrar y salir del modo soporte deja la consola funcionando.

> **Efecto al actualizar:** cada persona tendrá que volver a entrar **una vez**, porque el refresh viejo estaba en el navegador.
>
> **Limitación:** un frontend en OTRO dominio (Vercel/Netlify, retirados en la decisión D-12) no puede usar la cookie. GestorPro se sirve desde un solo origen.

---

## 5. Verificación en dos pasos del personal de la plataforma

**Por qué.** Quien tiene `is_platform_admin` puede entrar en modo soporte a cualquier empresa: su contraseña sola no basta. Ahora:

1. **Contraseña**, y luego el **código de 6 dígitos** de una app autenticadora (Google o Microsoft Authenticator, 1Password…).
2. Entre los dos pasos, el navegador solo tiene un `mfa_token` firmado de 5 minutos. No sirve como sesión y muere si cambia la contraseña.

**Cómo funciona** (`core/identity/mfa.py`):

- TOTP estándar (RFC 6238, verificado con el vector de prueba del RFC), sin dependencias nuevas.
- Se tolera ±30 s de desfase del reloj del celular.
- **Un código no se puede reutilizar**, ni en la app ni en el admin.
- Los códigos fallidos cuentan para el bloqueo por cuenta.

**La clave se crea solo en el servidor**, nunca desde el login. Si el login la ofreciera, quien robara la contraseña de alguien nuevo podría registrar su propio celular.

```
python manage.py platform_admin persona@gestorpro.co              # da acceso y muestra la clave UNA vez
python manage.py platform_admin persona@gestorpro.co --reset-2fa  # perdió el celular: clave nueva
```

- **El admin de Django** también pide el código. Si no lo pidiera, sería una puerta trasera sin 2FA.
- **Las sesiones abiertas del personal** se cerraron con una migración: la próxima vez entran con código.
- **Los usuarios de las empresas no cambian.** Para ellos, la verificación en dos pasos queda como opción futura.

---

## 6. Dependencias

`pip-audit` encontró vulnerabilidades conocidas en seis paquetes, todos actualizados:

| Paquete | Antes | Ahora |
|---|---|---|
| Django | 6.0.4 | 6.0.8 |
| Django REST framework | 3.17.1 | 3.17.2 |
| PyJWT | 2.12.1 | 2.15.0 |
| Pillow | 12.2.0 | 12.3.0 |
| sqlparse | 0.5.5 | 0.6.0 |
| anyio | 4.13.0 | 4.14.2 |

**Frontend:**

- `axios` pasa de 1.15 a 1.20 y `react-router` de 7.14 a 7.18 (advertencias de severidad alta).
- Lo que llega al navegador queda en **0 vulnerabilidades**.
- Quedan avisos en `vitest`, la herramienta de pruebas, que no se despliega. Su corrección exige un salto de versión mayor que hoy deja un lockfile que `npm ci` rechaza; queda pendiente.

**CI (nuevo job obligatorio):**

- `pip-audit -r requirements.txt`;
- `npm audit --omit=dev --audit-level=high`;
- un `npm audit` completo, solo informativo.

---

## 7. Revisión OWASP ASVS 4.0.3, nivel 2

Esta es una revisión de los capítulos aplicables a GestorPro: dice qué está cubierto, con qué y qué falta. **No es una certificación**: una auditoría externa sigue siendo recomendable antes de manejar muchos clientes.

| Capítulo | Estado | Evidencia / lo que falta |
|---|---|---|
| **V1 Arquitectura** | Parcial | Capas con contratos verificados en CI (import-linter), aislamiento en 5 capas + RLS, documentos 01–14. **Falta:** un modelo de amenazas formal. |
| **V2 Autenticación** | Parcial | Mínimo 12 caracteres, contraseñas comunes y similares al correo rechazadas, bloqueo por cuenta, límites por IP, recuperación que no revela cuentas, enlaces de un solo uso de 24 h, 2FA para el personal. **Falta:** revisar contraseñas filtradas (Have I Been Pwned) y 2FA opcional para dueños. |
| **V3 Sesiones** | Cumple | Refresh en cookie httpOnly/SameSite=Strict/Secure, rotación y revocación, logout real, cambio de contraseña o restablecimiento que cierra las demás sesiones, suspensión de membresía o empresa efectiva en la siguiente petición, sesiones de soporte de 30 min. Nota: el token corto (15 min) está en `localStorage`. |
| **V4 Control de acceso** | Cumple | Permisos por método validados en backend, módulos y plan validados en backend, aislamiento por empresa en la app y en PostgreSQL (RLS), 90+ tests de aislamiento, soporte de solo lectura. |
| **V5 Validación y codificación** | Cumple | Serializers en todo, precios, costos e impuestos calculados en el servidor, ORM sin SQL armado a mano, React escapa por defecto + CSP estricta, CSV exportado protegido contra fórmulas, importación con tamaño y filas acotados. |
| **V6 Criptografía** | Parcial | Contraseñas con PBKDF2 (Django), secretos por variables de entorno, tokens firmados, TOTP con comparación en tiempo constante. **Falta:** cifrar en reposo la clave TOTP (hoy en claro en la base, accesible solo con acceso a la base). |
| **V7 Errores y registros** | Cumple | DEBUG apagado fuera de desarrollo, sin trazas al usuario, auditoría y eventos de seguridad de **solo inserción** (triggers en PostgreSQL), registro de logins, bloqueos, 2FA y accesos de soporte. |
| **V8 Protección de datos** | Cumple | `Cache-Control: no-store` en la API, nada sensible en `localStorage` salvo el token corto, sin datos de negocio en la consola de plataforma, copias de seguridad verificadas. |
| **V9 Comunicaciones** | Parcial | En producción: HTTPS, HSTS y cookies Secure. **Falta:** HTTPS en la edición local (red local por HTTP; ver pendientes). |
| **V10 Código malicioso** | Cumple | Dependencias fijadas a versión exacta, auditoría obligatoria en CI, sin librerías nuevas para 2FA. |
| **V11 Lógica de negocio** | Cumple | Concurrencia probada con hilos reales (Fase 11), invariantes contables, límites de intentos, límites del plan con bloqueo. |
| **V12 Archivos** | Parcial | Importación con tamaño, filas y tipo acotados. **Falta:** revisar la validación de imágenes subidas (logo, productos). |
| **V13 API** | Cumple | JWT por cabecera, CORS restringido, esquema no público en producción, verificación de origen en el único endpoint que usa cookie. |
| **V14 Configuración** | Cumple | `check --deploy` en CI, CSP y cabeceras, sin credenciales por defecto ni superusuario automático, sin `wipe_db`, rol de base con mínimo privilegio (sin TRUNCATE ni DDL). |

---

## 8. Lo que tienes que hacer

1. **En tu PC.** Cierra las ventanas de GestorPro y ejecuta **`instalar.bat`**: hay migraciones y dependencias nuevas.
2. **Consola de plataforma.** Después de actualizar, ejecuta otra vez:

   ```
   python manage.py platform_admin TU-CORREO
   ```

   Agrega la clave que muestra en tu app autenticadora. Desde ahí, entras con contraseña + código.
3. **Todas las personas** vuelven a iniciar sesión una vez (la sesión pasó a la cookie).
4. **Edición local de La Favorita.** Usa `actualizar.bat`; el rol de base de datos se crea solo.
5. **Railway.** Si el usuario de la base no es superusuario, crea el rol (sección 1) antes de desplegar.

## 9. Pruebas

**Tests nuevos:**

| Archivo | Tests | Qué cubre |
|---|---|---|
| `tests/isolation/test_rls.py` | 12 | SQL crudo, manager sin filtro, inserciones y movimientos entre empresas, TRUNCATE y DDL negados, savepoints revertidos, cobertura de todas las tablas |
| `tests/isolation/test_security_headers.py` | 4 | CSP en la SPA y en la API, sin documentación pública, `no-store` |
| `tests/isolation/test_refresh_cookie.py` | 5 | — |
| `tests/isolation/test_platform_mfa.py` | 10 | Incluye el vector del RFC y el admin de Django |
| `tests/core/test_auth_and_sessions.py` | +2 | Bloqueo por cuenta |
| `tests/platform/test_local_edition.py` | +2 | Rol de RLS en la edición local |

**Tests existentes actualizados** a la nueva realidad, sin relajar ninguna verificación:

- **Lectura global en tests:** los tests que leen datos de varias empresas ahora lo declaran (`s.globally`).
- **Refresh:** se lee de la cookie.
- **Personal de plataforma:** entra con código.

## 10. Pendiente

- **HTTPS en la edición local:** certificado local para la red del negocio.
- **2FA opcional** para dueños y administradores de empresa.
- **Contraseñas filtradas:** revisión contra Have I Been Pwned (k-anonimato).
- **Clave TOTP:** cifrarla en reposo.
- **Imágenes subidas:** revisar su validación.
- **`vitest` 4:** cuando npm resuelva el lockfile.
- **Modelo de amenazas formal** y auditoría externa antes de escalar.
