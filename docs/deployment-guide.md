# Guía de despliegue — FUNDCORSRD

El sitio se despliega en dos partes: el **frontend** (sitio estático) va en la cuenta de Network Solutions del cliente; el **backend** (Django) vive en PythonAnywhere. Son dos hostings separados — cada uno se actualiza con su propio procedimiento (secciones 1-3 para el frontend en Network Solutions, sección 3-bis para el backend en PythonAnywhere).

## 0. Antes de empezar — verificar con Network Solutions

Estos puntos no están confirmados desde este entorno de desarrollo y deben verificarse una sola vez, directamente en el panel de Network Solutions o con su soporte, antes del primer despliegue:

1. **Versión de Python disponible** y el mecanismo exacto para montar una app Python (lo más probable es un sistema tipo Passenger/WSGI, donde el panel pide un archivo `passenger_wsgi.py` — ya incluido en `backend/passenger_wsgi.py`).
2. **Dónde se puede montar la app Python**: idealmente en un subdominio propio, por ejemplo `api.fundcorsrd.com`, apuntando únicamente a la carpeta `backend/`. El dominio principal (`fundcorsrd.com`) se deja para los archivos estáticos del frontend. (Un subdominio evita ambigüedades de cómo el panel maneja las rutas — es la opción más simple y confiable).
3. **Conexiones salientes permitidas**: el backend necesita poder hacer peticiones HTTP salientes hacia `190.166.228.161:2103` (el caster NTRIP, para el mapa) y hacia un servidor SMTP (para los correos de verificación/inscripción). Si el hosting bloquea alguna de las dos, hay que pedir que la habiliten, o usar un proveedor de correo transaccional por API HTTPS en su lugar.
4. **Persistencia del sistema de archivos**: la base de datos (`backend/data/db.sqlite3`) debe sobrevivir entre despliegues y reinicios de la app. Confirmar que la carpeta de la aplicación no se borra/reemplaza completamente en cada actualización.
5. **Acceso SSH** (además de FTP/SFTP): si existe, el script de despliegue (`scripts/deploy.sh`) puede automatizar los pasos de instalación/migración también en el servidor. Si no existe, esos pasos puntuales (ver paso 4 abajo) se hacen manualmente por el panel — no es un bloqueante, solo hace falta la primera vez y cuando cambian las dependencias o el modelo de datos. (Comprobado el 2026-08-17: el endpoint de `ftp.fundcorsrd.com:2222` es un servidor solo-SFTP sin shell, así que **por esa vía no hay SSH**; si hace falta shell, hay que pedirlo a soporte de Network Solutions).

## 1. Configuración inicial del backend (una sola vez)

1. En el panel de Network Solutions, crear la app Python apuntando a la carpeta `backend/` (o subir `backend/` primero por FTP/SFTP y luego apuntar la app ahí).
2. Dentro del entorno virtual que provea el panel:
   ```bash
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py createsuperuser
   ```
   El `createsuperuser` crea la primera cuenta de administrador — con ella se entra a `/django-admin/`. El registro de agrimensores se activa solo (ver sección 4), pero esta cuenta sigue siendo útil para desactivar una cuenta problemática si hace falta.
3. Configurar las variables de entorno en el panel (ver `backend/.env.example` para la lista completa con explicación de cada una). Como mínimo:
   - `DJANGO_SECRET_KEY` — generar uno nuevo y real, nunca reusar el de desarrollo.
   - `DJANGO_SETTINGS_MODULE=config.settings.prod`
   - `DJANGO_ALLOWED_HOSTS` — el hostname real del backend, ej. `api.fundcorsrd.com`.
   - `FRONTEND_ORIGIN` — el origen real del frontend, ej. `https://fundcorsrd.com`.
   - `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` — credenciales SMTP reales, para que los correos de verificación/inscripción se envíen de verdad (en desarrollo solo se imprimen en consola).
   - Los 5 `DOWNLOAD_URL_*` (RINEX, Manzanero, Soluciones, Hojas, CORSDist) — si se quiere sobreescribir los enlaces actuales (ver la nota de "Riesgo residual" abajo). Si no se definen, el backend usa los enlaces reales actuales como valor por defecto.
   - `RECAPTCHA_SECRET_KEY` — **sin esto, el registro rechaza todas las solicitudes** (falla cerrado a propósito, en vez de aceptar en silencio la clave de prueba pública de Google). Hay que solicitar un par de claves real (site key + secret key) en https://www.google.com/recaptcha/admin para el dominio real de producción, con una cuenta de Google que tenga acceso a ese dominio — esto **no lo puede hacer nadie más que el cliente/dueño del dominio**. Una vez obtenida: poner la secret key aquí como `RECAPTCHA_SECRET_KEY`, y actualizar la constante `RECAPTCHA_SITE_KEY` en `frontend/src/js/config.js` con la site key correspondiente (esa sí es pública, va directo en el código del frontend, no como variable de entorno) antes de compilar y subir el frontend.
4. Reiniciar la app Python para que tome las variables de entorno (en hosting tipo Passenger, normalmente se hace tocando un archivo `tmp/restart.txt` dentro de la carpeta de la app — confirmar el método exacto con soporte de Network Solutions si el panel no tiene un botón de "Restart").

## 2. DNS

Agregar en el panel de DNS de Network Solutions un registro para el subdominio del backend (ej. `api`) apuntando al mismo hosting. Network Solutions es al mismo tiempo el registrador del dominio y el hosting, así que esto se hace desde el mismo panel.

## 3. Actualizar el sitio (`./scripts/deploy.sh`)

Después de la configuración inicial, para publicar cambios:

```bash
./scripts/deploy.sh --dry-run   # primero: muestra qué subiría y qué borraría, sin tocar el servidor
./scripts/deploy.sh             # el despliegue real
```

Este script:
1. Compila el frontend (`npm run build` dentro de `frontend/`). Si la máquina no tiene Node instalado, reutiliza el `frontend/dist/` ya compilado, pero **solo** si ningún archivo de `frontend/src/` es más nuevo que él; si el build está desactualizado, se detiene en vez de publicar una versión vieja en silencio.
2. Sube `frontend/dist/` por SFTP/FTP al `public_html` (o la carpeta que corresponda al dominio principal).
3. Sube los archivos de `backend/` por SFTP/FTP a la carpeta de la app Python.
4. Si hay acceso SSH configurado (ver variables al inicio del script), además ejecuta en el servidor `pip install -r requirements.txt`, `python manage.py migrate`, `python manage.py collectstatic`, y reinicia la app — en ese caso el flujo es realmente un solo comando.
5. Si no hay SSH, esos últimos pasos hay que hacerlos manualmente por el panel de Network Solutions **solo cuando cambien las dependencias (`requirements.txt`) o los modelos de datos** — una actualización normal de contenido/frontend no los necesita.

Los dos `mirror` van con `--delete`, es decir dejan la carpeta remota como copia exacta de la local: **todo lo que esté en esas rutas remotas y no en este repo se borra**. Por eso el script pide escribir `deploy` para confirmar antes de empezar, y por eso conviene pasar siempre primero por `--dry-run`.

Antes del primer uso, copiar `scripts/deploy.example.env` a `scripts/deploy.env` (no se sube a git) con las credenciales reales. La contraseña se puede dejar fuera del archivo: si `DEPLOY_FTP_PASS` no está definida, el script la pide al ejecutarse y así nunca queda escrita en disco.

Requiere `lftp` (`brew install lftp`), que es lo que hace el espejado tanto por FTP como por SFTP.

### Datos verificados de este servidor (2026-08-17)

- **Host:** `ftp.fundcorsrd.com` (resuelve a `66.96.147.168`) — **puerto 2222**, protocolo SFTP. El puerto no es el 22 por defecto, así que hay que declararlo explícitamente (`DEPLOY_FTP_PORT=2222`).
- El servidor se identifica como `SSH-2.0-ipage FTP Server`: es un endpoint **solo de transferencia de archivos, sin shell**. Por eso `DEPLOY_SSH_HOST` se deja vacío — no puede ejecutar `pip`/`migrate`/`collectstatic` remotamente, y esos pasos van por el panel.
- El servidor solo ofrece claves de host `ssh-rsa`/`ssh-dss`, que OpenSSH 8.8+ rechaza por defecto (falla con `no matching host key type found`). `deploy.sh` ya lo resuelve pasándole `-o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa` únicamente a esta conexión, sin alterar la configuración SSH global de la máquina.
- La raíz del sitio tiene un archivo `.membership` y una carpeta `stats/` (estadísticas de visitas tipo Webalizer) que genera y administra la propia plataforma de hosting — no son parte de este repo y la cuenta FTP no tiene permiso para borrarlos. `deploy.sh` los excluye explícitamente del espejado (`--exclude-glob .membership --exclude-glob stats/`) para que `mirror --delete` no intente tocarlos; sin esa exclusión, el intento de borrado falla con "Permission denied" y aborta todo el despliegue (detectado y corregido el 2026-08-24).

## 3-bis. Actualizar el backend (PythonAnywhere)

El backend está en una cuenta de PythonAnywhere de pago (plan Hacker o superior), subido ahí manualmente (no como clon de git). Esto se puede convertir a un clon de git **una sola vez**, y a partir de ahí cada actualización se reduce a un `git pull`.

### Paso único: convertir la carpeta actual en un clon de git

Desde la consola Bash de PythonAnywhere (o por SSH, si la usas desde tu propia terminal — con un plan de pago tienes acceso SSH; el host y las instrucciones exactas están en la pestaña **Account → SSH access** del panel):

```bash
cd ~/ruta-a-tu-carpeta-del-backend   # confirma la ruta real con: ls ~ y con la pestaña "Web" del panel (Source code / Working directory)

# Respaldo de seguridad antes de tocar nada (por si algo no cuadra):
cp -r . ../backend-respaldo-$(date +%Y%m%d)

git init
git remote add origin https://github.com/laurasosa02/fundcors-rd.git
git fetch origin
git reset --hard origin/main
```

`git reset --hard` solo toca archivos que están en el repositorio — `.env`, la base de datos (`db.sqlite3`) y el entorno virtual no están versionados (están en `.gitignore`), así que no se tocan. Aun así, revisa con `git status` que no falte nada esperado antes de continuar, y borra la carpeta de respaldo (`backend-respaldo-...`) una vez que confirmes que todo sigue funcionando.

Como el repositorio completo incluye tanto `frontend/` como `backend/`, y esta carpeta en PythonAnywhere debe contener solo el backend, hace falta decirle a git que solo mantenga actualizada la subcarpeta `backend/` dentro de esta carpeta. La forma más simple: en vez de clonar el repo completo aquí, mover el working directory de la app Python (configurado en la pestaña **Web** del panel) para que apunte a `~/fundcors-rd/backend` después de clonar el repo completo una vez en `~/fundcors-rd`:

```bash
cd ~
git clone https://github.com/laurasosa02/fundcors-rd.git
# copia tu .env existente (y cualquier otro archivo local que no esté en git) a ~/fundcors-rd/backend/
```

Después de esto, actualiza en la pestaña **Web** del panel de PythonAnywhere la ruta del código fuente / working directory / virtualenv para que apunten dentro de `~/fundcors-rd/backend/`, y borra la carpeta manual anterior una vez confirmes que la app sigue funcionando igual.

### Actualizar después de cada cambio

```bash
cd ~/fundcors-rd
git pull origin main
cd backend
pip install -r requirements.txt   # solo si requirements.txt cambió
python manage.py migrate          # solo si hay migraciones nuevas
```

Y por último, recargar la app — con un plan de pago hay dos formas:

- **Manual:** botón **Reload** en la pestaña **Web** del panel de PythonAnywhere (siempre funciona, un clic).
- **Automatizado:** generando un token en **Account → API Token**, se puede recargar por línea de comandos (o meterlo como último paso de un script propio) sin entrar al panel:
  ```bash
  curl -X POST -H "Authorization: Token TU_TOKEN_AQUI" \
    https://www.pythonanywhere.com/api/v0/user/TU_USUARIO/webapps/TU_DOMINIO/reload/
  ```

## 4. Activación de cuentas de agrimensores

El registro **no requiere ninguna aprobación manual**. El flujo es automático:

1. El usuario completa el formulario de registro (el reCAPTCHA se valida en el momento).
2. Le llega un correo pidiéndole que verifique su dirección de correo.
3. En cuanto hace clic en ese enlace (y confirma en la página que se abre — un solo clic, existe esa pantalla intermedia para que un escáner de enlaces de correo/antivirus no pueda activar la cuenta él solo al abrir el correo automáticamente antes de que el usuario lo haga), **su cuenta queda activa de inmediato** y ya puede iniciar sesión y ver las Descargas Autorizadas.

Además, cuando alguien se registra, `ADMIN_NOTIFY_EMAIL` recibe un correo informativo (nombre, cédula, teléfono, correo) — es solo para que el staff de FUNDCORSRD esté al tanto, no hay nada que aprobar ni ningún enlace que haga falta pulsar ahí.

Si en algún momento hay que **desactivar una cuenta** (por ejemplo, un mal uso comprobado), entrando a `https://api.fundcorsrd.com/django-admin/` con la cuenta creada en el paso 1, en la sección Users se puede usar la acción masiva "Rechazar usuarios seleccionados" sobre la cuenta en cuestión — eso sí bloquea el login de inmediato, incluso si esa persona ya había verificado su correo antes.

## 5. Riesgo residual: enlaces de Dropbox

Las "Descargas Autorizadas" (Mapa Manzanero, Soluciones Red FC, Hojas Topográficas) son enlaces de Dropbox existentes, no archivos alojados por este proyecto — el backend controla **quién ve el enlace**, pero una vez que un enlace es revelado a un usuario aprobado, ese enlace en sí no expira ni está firmado, así que técnicamente podría ser reenviado fuera de la aplicación. Esta es una decisión ya tomada conscientemente (mantener los enlaces existentes en vez de migrar los archivos a almacenamiento propio). Mitigación recomendada: regenerar los enlaces de Dropbox periódicamente (cada pocos meses, o si se sospecha una filtración) y actualizar las variables `DOWNLOAD_URL_MANZANERO`, `DOWNLOAD_URL_SOLUCIONES`, `DOWNLOAD_URL_HOJAS` en el panel — invalida los enlaces viejos sin tocar código.

## 6. Verificación post-despliegue

- `curl -i https://api.fundcorsrd.com/downloads/` sin cookie de sesión debe devolver 401 y el cuerpo no debe contener `dropbox.com` ni `rinex.hairo` en ningún lado.
- Registrar una cuenta de prueba real con el reCAPTCHA real visible y resuelto (si el sitio muestra el checkbox de prueba de Google en vez del real, es porque `RECAPTCHA_SITE_KEY` en `frontend/src/js/config.js` sigue en el valor de prueba — falta actualizarlo). Confirmar que llegan DOS correos: el de verificación de correo (al usuario) y el informativo de nuevo registro (al `ADMIN_NOTIFY_EMAIL`, sin enlaces de acción). Intentar iniciar sesión antes de verificar el correo — debe rechazar con el mensaje de "verifica tu correo". Hacer clic en el enlace de verificación y confirmar en la página que aparece — el login debe funcionar inmediatamente después, sin ningún paso de aprobación, y deben aparecer los 5 enlaces reales de Descargas Autorizadas.
- Revisar `https://api.fundcorsrd.com/stations/` — debe devolver estaciones reales (no una lista vacía) si el caster NTRIP es alcanzable desde el hosting, y las ventanas emergentes de cada estación en el mapa deben mostrar latitud/longitud y la hora de la última actualización debe verse en la leyenda.
