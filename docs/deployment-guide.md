# Guía de despliegue — FUNDCORSRD en Network Solutions

Esta guía asume que el frontend (sitio estático) y el backend (Django) se despliegan **juntos, en la misma cuenta de Network Solutions**, ya que Network Solutions soporta Python de forma nativa. No se necesita contratar un segundo hosting.

## 0. Antes de empezar — verificar con Network Solutions

Estos puntos no están confirmados desde este entorno de desarrollo y deben verificarse una sola vez, directamente en el panel de Network Solutions o con su soporte, antes del primer despliegue:

1. **Versión de Python disponible** y el mecanismo exacto para montar una app Python (lo más probable es un sistema tipo Passenger/WSGI, donde el panel pide un archivo `passenger_wsgi.py` — ya incluido en `backend/passenger_wsgi.py`).
2. **Dónde se puede montar la app Python**: idealmente en un subdominio propio, por ejemplo `api.fundcorsrd.com`, apuntando únicamente a la carpeta `backend/`. El dominio principal (`fundcorsrd.com`) se deja para los archivos estáticos del frontend. (Un subdominio evita ambigüedades de cómo el panel maneja las rutas — es la opción más simple y confiable).
3. **Conexiones salientes permitidas**: el backend necesita poder hacer peticiones HTTP salientes hacia `190.166.228.161:2103` (el caster NTRIP, para el mapa) y hacia un servidor SMTP (para los correos de aprobación/inscripción). Si el hosting bloquea alguna de las dos, hay que pedir que la habiliten, o usar un proveedor de correo transaccional por API HTTPS en su lugar.
4. **Persistencia del sistema de archivos**: la base de datos (`backend/data/db.sqlite3`) debe sobrevivir entre despliegues y reinicios de la app. Confirmar que la carpeta de la aplicación no se borra/reemplaza completamente en cada actualización.
5. **Acceso SSH** (además de FTP/SFTP): si existe, el script de despliegue (`scripts/deploy.sh`) puede automatizar los pasos de instalación/migración también en el servidor. Si no existe, esos pasos puntuales (ver paso 4 abajo) se hacen manualmente por el panel — no es un bloqueante, solo hace falta la primera vez y cuando cambian las dependencias o el modelo de datos.

## 1. Configuración inicial del backend (una sola vez)

1. En el panel de Network Solutions, crear la app Python apuntando a la carpeta `backend/` (o subir `backend/` primero por FTP/SFTP y luego apuntar la app ahí).
2. Dentro del entorno virtual que provea el panel:
   ```bash
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py createsuperuser
   ```
   El `createsuperuser` crea la primera cuenta de administrador — con ella se entra a `/django-admin/` para aprobar/rechazar registros de agrimensores.
3. Configurar las variables de entorno en el panel (ver `backend/.env.example` para la lista completa con explicación de cada una). Como mínimo:
   - `DJANGO_SECRET_KEY` — generar uno nuevo y real, nunca reusar el de desarrollo.
   - `DJANGO_SETTINGS_MODULE=config.settings.prod`
   - `DJANGO_ALLOWED_HOSTS` — el hostname real del backend, ej. `api.fundcorsrd.com`.
   - `FRONTEND_ORIGIN` — el origen real del frontend, ej. `https://fundcorsrd.com`.
   - `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` — credenciales SMTP reales, para que los correos de aprobación/inscripción se envíen de verdad (en desarrollo solo se imprimen en consola).
   - Los 4 `DOWNLOAD_URL_*` — si se quiere sobreescribir los enlaces actuales (ver la nota de "Riesgo residual" abajo). Si no se definen, el backend usa los enlaces reales actuales como valor por defecto.
4. Reiniciar la app Python para que tome las variables de entorno (en hosting tipo Passenger, normalmente se hace tocando un archivo `tmp/restart.txt` dentro de la carpeta de la app — confirmar el método exacto con soporte de Network Solutions si el panel no tiene un botón de "Restart").

## 2. DNS

Agregar en el panel de DNS de Network Solutions un registro para el subdominio del backend (ej. `api`) apuntando al mismo hosting. Network Solutions es al mismo tiempo el registrador del dominio y el hosting, así que esto se hace desde el mismo panel.

## 3. Actualizar el sitio (`./scripts/deploy.sh`)

Después de la configuración inicial, para publicar cambios:

```bash
./scripts/deploy.sh
```

Este script:
1. Compila el frontend (`npm run build` dentro de `frontend/`).
2. Sube `frontend/dist/` por SFTP/FTP al `public_html` (o la carpeta que corresponda al dominio principal).
3. Sube los archivos de `backend/` por SFTP/FTP a la carpeta de la app Python.
4. Si hay acceso SSH configurado (ver variables al inicio del script), además ejecuta en el servidor `pip install -r requirements.txt`, `python manage.py migrate`, `python manage.py collectstatic`, y reinicia la app — en ese caso el flujo es realmente un solo comando.
5. Si no hay SSH, esos últimos pasos hay que hacerlos manualmente por el panel de Network Solutions **solo cuando cambien las dependencias (`requirements.txt`) o los modelos de datos** — una actualización normal de contenido/frontend no los necesita.

Antes del primer uso, copiar `scripts/deploy.example.env` a `scripts/deploy.env` (no se sube a git) con las credenciales FTP/SSH reales.

## 4. Cómo aprobar cuentas de agrimensores

Cuando alguien se registra desde el sitio, queda en estado "pendiente" y **no puede iniciar sesión ni ver las Descargas Autorizadas** hasta ser aprobado. Dos formas de aprobar:

- **Correo con un clic**: el registro dispara un correo a `ADMIN_NOTIFY_EMAIL` con botones "Aprobar"/"Rechazar" — un clic basta, sin necesidad de entrar a ningún panel.
- **Panel de administración**: entrando a `https://api.fundcorsrd.com/django-admin/` con la cuenta creada en el paso 1, en la sección Users se puede filtrar por estado y usar las acciones masivas "Aprobar seleccionados"/"Rechazar seleccionados".

## 5. Riesgo residual: enlaces de Dropbox

Las "Descargas Autorizadas" (Mapa Manzanero, Soluciones Red FC, Hojas Topográficas) son enlaces de Dropbox existentes, no archivos alojados por este proyecto — el backend controla **quién ve el enlace**, pero una vez que un enlace es revelado a un usuario aprobado, ese enlace en sí no expira ni está firmado, así que técnicamente podría ser reenviado fuera de la aplicación. Esta es una decisión ya tomada conscientemente (mantener los enlaces existentes en vez de migrar los archivos a almacenamiento propio). Mitigación recomendada: regenerar los enlaces de Dropbox periódicamente (cada pocos meses, o si se sospecha una filtración) y actualizar las variables `DOWNLOAD_URL_MANZANERO`, `DOWNLOAD_URL_SOLUCIONES`, `DOWNLOAD_URL_HOJAS` en el panel — invalida los enlaces viejos sin tocar código.

## 6. Verificación post-despliegue

- `curl -i https://api.fundcorsrd.com/downloads/` sin cookie de sesión debe devolver 401 y el cuerpo no debe contener `dropbox.com` ni `rinex.hairo` en ningún lado.
- Registrar una cuenta de prueba real, confirmar que llega el correo de notificación, aprobarla, confirmar que llega el correo de aprobación, iniciar sesión y confirmar que aparecen los 4 enlaces reales.
- Revisar `https://api.fundcorsrd.com/stations/` — debe devolver estaciones reales (no una lista vacía) si el caster NTRIP es alcanzable desde el hosting.
