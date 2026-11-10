# Documento 15 — Despliegue gratis en la nube (Render + Neon)

| | |
|---|---|
| **Estado** | Implementado en la rama `claude/zen-johnson-hhz8hm` |
| **Fecha** | 2026-11-10 |
| **Para qué** | Piloto del primer mes de La Favorita en la nube, sin costo, con soporte remoto |

**Arquitectura:**

- **La app** corre en **Render**, en el plan gratis.
- **La base de datos** va en **Neon**, en el plan gratis: 1 GB y no vence.

La base gratis de Render no sirve: vence a los 30 días y luego se borra.

**Cuando haya pago**, se pasa a Railway (unos US$5 al mes) o al plan pago de Render, copiando la base con `pg_dump` y `pg_restore`.

---

## 1. Lo que se cambió en el código para la nube

| Cambio | Por qué |
|---|---|
| `render.yaml` | Blueprint de Render, en plan gratis y región Virginia (la misma zona que Neon, `us-east-1`). Compila, recolecta los estáticos y al arrancar migra y levanta gunicorn (2 workers × 2 hilos). |
| `GET /api/health/` | Chequeo de salud del proveedor y de un monitor externo. No consulta la base ni requiere sesión. |
| `config/settings/prod.py` | **Dominio:** toma `RENDER_EXTERNAL_HOSTNAME` y lo agrega a `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`. **Enlaces:** lo usa como `FRONTEND_URL` si no se fijó otro. **HTTPS:** exime `/api/health/` de la redirección. **Clave:** acepta la `SECRET_KEY` de 256 bits que genera Render (44 caracteres; antes se exigían 50) y rechaza claves repetitivas. |
| `config/settings/base.py` | **Conexión:** `conn_health_checks=True`, porque Neon suspende la base sin uso y la conexión se reabre sola. **Poolers:** se **rechaza** una URL de pooler (`-pooler.` o `pgbouncer=true`). Row-Level Security fija el rol y la empresa en la sesión de PostgreSQL, y un pooler en modo transacción las mezclaría entre peticiones. |
| `core/tenancy/rls.py` | **Corrige un fallo real en PostgreSQL 16+ (Neon).** Quien crea un rol con `CREATEROLE` queda como administrador del rol, pero sin permiso de `SET ROLE`. `pg_has_role(…, 'MEMBER')` decía "sí" y el `SET ROLE` fallaba en cada consulta. Ahora se verifica `SET`, y el dueño se da el permiso a sí mismo (`GRANT gestorpro_rls TO CURRENT_USER`). |
| `platform_admin --create` | En Render gratis no hay consola. La cuenta de soporte se crea desde tu PC contra la base de Neon: pide nombre y contraseña, nunca crea un superusuario y muestra la clave 2FA una vez. |

**Probado** con un dueño sin superusuario y con `CREATEROLE`, como en Neon, sobre PostgreSQL 16, con la configuración de producción y gunicorn:

- `migrate` crea el rol, el dueño se da el permiso y quedan 30 tablas con política.
- La app consulta como `gestorpro_rls`.
- La invitación usa el dominio de Render.
- `/api/health/` responde 200 por HTTP interno.
- HTTP redirige a HTTPS y un host ajeno da 400.
- Aceptar la invitación, el login y `/api/auth/me/` responden bien, con cabeceras de seguridad y la cookie `gp_refresh`.

Tests nuevos: `tests/platform/test_cloud_deploy.py` y `test_platform_admin_can_create_the_account_on_purpose`.

---

## 2. Paso a paso

### A. Base de datos en Neon

1. Entra a neon.com y crea una cuenta gratis (con GitHub o Google).
2. Crea un proyecto llamado `gestorpro`, en la región **AWS US East (N. Virginia)**.
3. Abre **Connect**, **desactiva "Connection pooling"** y copia la cadena de conexión. Se ve así:
   `postgresql://neondb_owner:CLAVE@ep-xxxx.us-east-1.aws.neon.tech/neondb?sslmode=require`

   **No debe decir `-pooler`.** Si lo dice, GestorPro no arranca y avisa por qué.

### B. Código en la rama principal

Render despliega la rama `main` (ver `render.yaml`). El trabajo se lleva a `main` con un pull request.

### C. App en Render

1. Entra a render.com y crea una cuenta con **GitHub**, la misma cuenta dueña del repositorio. Autoriza el acceso al repositorio `gestorpro`.
2. Ve a **New → Blueprint** y elige el repositorio. Render lee `render.yaml`.
3. Pide **DATABASE_URL**: pega la cadena de Neon del paso A.3. Luego **Apply**.
4. Espera la primera compilación, de unos 5 minutos. La dirección queda como `https://gestorpro-xxxx.onrender.com`.
5. Revisa que funcione: `https://gestorpro-xxxx.onrender.com/api/health/` debe mostrar `{"ok": true}`.

### D. Configuración inicial desde tu PC

En Render gratis no hay consola, así que los comandos se ejecutan en tu PC, en la carpeta `gestorpro` de la instalación de pruebas, apuntando a Neon:

```
set DATABASE_URL=postgresql://neondb_owner:CLAVE@ep-xxxx.us-east-1.aws.neon.tech/neondb?sslmode=require
set FRONTEND_URL=https://gestorpro-xxxx.onrender.com
venv\Scripts\python manage.py platform_admin TU-CORREO --create
venv\Scripts\python manage.py onboard_tenant "Panadería La Favorita" CORREO-DE-LA-DUEÑA --vertical bakery --plan business --city Bogotá
venv\Scripts\python manage.py load_starter_catalog panaderia-la-favorita
```

- El **primero** crea tu acceso de soporte y muestra la clave del Authenticator, **una vez**.
- El **segundo** crea la empresa y muestra el **enlace de invitación** de la dueña.
- El **tercero** carga el catálogo inicial de panadería.

Las variables `set` solo duran en esa ventana de comandos: ciérrala al terminar para no apuntar a la nube por error.

### E. Que no se duerma (opcional)

Render gratis apaga la app tras 15 minutos sin visitas, y despertar tarda cerca de 1 minuto. Un monitor gratis (por ejemplo, UptimeRobot) que visite `/api/health/` cada 10 minutos la mantiene despierta. Las 750 horas gratis al mes alcanzan para tenerla encendida todo el mes. Revisa las condiciones de uso de Render antes de dejarlo así.

---

## 3. Limitaciones del piloto gratis

| Limitación | Cómo se maneja |
|---|---|
| La app se duerme tras 15 min sin uso | El monitor externo (E), o avisar a la dueña que la primera apertura tarda |
| El disco de Render no es permanente | Durante el piloto no se suben fotos de productos ni logo. Ventas, caja e inventario están en Neon y no se pierden |
| Sin internet no funciona | Igual que con cualquier nube. Un celular con datos sirve de respaldo |
| Sin correo configurado | "¿Olvidaste tu contraseña?" no envía correos. La dueña recupera su acceso con un enlace que generas desde la consola de plataforma |
| Copias de seguridad | Neon guarda historial de cambios para restaurar, con alcance limitado en el plan gratis. Antes de pasar a pago, hay que hacer una copia con `pg_dump` |
