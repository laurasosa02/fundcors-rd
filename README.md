# FUNDCORSRD — Portal Web

Portal institucional de FUNDCORSRD (Fundación para el Establecimiento de la Red de Estaciones Permanentes de la República Dominicana): mapa en tiempo real de la red CORS, información institucional, formulario de inscripción, y un área de acceso para agrimensores con descargas autorizadas tras aprobación manual.

Implementación standalone (sin WordPress): frontend en HTML/CSS/JS puro + backend en Django (Python), pensados para desplegarse juntos en una sola cuenta de hosting con soporte Python nativo (Network Solutions).

El paquete de diseño original que sirvió de referencia para esta recreación vive en [`design_handoff_portal_fundcorsrd/`](design_handoff_portal_fundcorsrd/README.md) — se conserva como referencia histórica, no es el código de producción.

## Estructura

```
frontend/    Sitio estático (HTML/CSS/JS vanilla + un paso de build con esbuild)
backend/     API en Django (auth con aprobación manual, proxy del mapa NTRIP, descargas gateadas)
docs/        Guía de despliegue
scripts/     Script de despliegue de un solo comando
```

Ver [`frontend/`](frontend/) y [`backend/`](backend/) para más detalle de cada parte.

## Desarrollo local

Requiere Node.js 20+ y Python 3.11+.

**Backend** (sirve la API en `http://localhost:8000`):

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_SECRET_KEY=dev-only-local-secret
python manage.py migrate
python manage.py createsuperuser   # crea el primer admin, para aprobar cuentas desde /django-admin/
python manage.py runserver 127.0.0.1:8000
```

**Frontend** (sirve el sitio estático en `http://localhost:5500`, en otra terminal):

```bash
cd frontend
npm install
npm run build   # genera frontend/dist/
npm run dev     # sirve frontend/src/ sin bundlear, para iterar rápido
```

Con ambos corriendo, abre `http://localhost:5500` (o `http://localhost:8000/django-admin/` para el panel de administración). El registro de una cuenta queda en estado "pendiente" hasta que un admin la aprueba desde `/django-admin/` (o desde el enlace de un clic que llega por correo — en desarrollo, los correos solo se imprimen en la consola del backend, no se envían de verdad).

## Despliegue a producción

Ver [`docs/deployment-guide.md`](docs/deployment-guide.md) — pensado para desplegar frontend y backend juntos en la cuenta de Network Solutions existente del cliente, sin necesitar un segundo hosting.

## Seguridad

- Autenticación server-side real (sesiones de Django, contraseñas con Argon2, CSRF activo, rate-limiting/bloqueo de intentos con django-axes).
- Las 4 URLs de "Descargas Autorizadas" solo se entregan a cuentas con sesión activa y estado `approved` — nunca viajan en el HTML/JS inicial (verificado: `grep -r "dropbox.com\|rinex.hairo" frontend/dist/` debe devolver vacío).
- El mapa de estaciones consulta el caster NTRIP desde el backend (no desde el navegador), evitando depender de proxies públicos de terceros.
- Ver la sección "Riesgo residual" en `docs/deployment-guide.md` sobre los enlaces de Dropbox (no firmados, se recomienda rotarlos periódicamente).
