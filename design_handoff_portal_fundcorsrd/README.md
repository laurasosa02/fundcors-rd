# Handoff: Portal Web FUNDCORSRD

## Overview
Portal institucional de FUNDCORSRD (Fundación para el Establecimiento de la Red de Estaciones Permanentes de la República Dominicana). Sitio de una sola página con: hero, secciones "Nosotros" (Quiénes Somos, Inscripción, Preguntas Frecuentes, Contactos), Estado Actual (mapa de estaciones GNSS/CORS), Descargas, y Acceso (login/registro de agrimensores vía Ultimate Member, con vista de Descargas Autorizadas tras iniciar sesión).

Destino final: implementación standalone en HTML/CSS/JS puro en `/Users/sosa/Dropbox/fundacors-rd`, para desktop y móvil — **no** WordPress/Elementor (esa fue una integración temporal; el sitio real debe ser independiente).

## About the Design Files
Los archivos HTML en este paquete son **referencias de diseño**, construidas como prototipos para validar look & feel, contenido y comportamiento — no son código de producción para copiar tal cual. La tarea es **recrear este diseño como una implementación limpia en HTML/CSS/JS vanilla** (sin frameworks a menos que se decida agregar uno), optimizada para performance, seguridad y animaciones fluidas, funcionando en desktop y móvil.

## Fidelity
**Alta fidelidad (hifi).** Colores, tipografía, espaciados y layout están definidos y deben respetarse exactamente (ver Design Tokens). Recrear pixel a pixel usando CSS moderno (grid/flexbox, custom properties), no aproximar.

## Requisitos no funcionales (prioridad del cliente)
- **Responsive real**: layouts propios para desktop y móvil (no solo reflow) — el prototipo ya incluye breakpoints, revisar `@media (max-width:980px)` y `@media (max-width:640px)` en cada archivo.
- **Seguridad**: este sitio maneja autenticación de agrimensores y descarga de archivos técnicos (RINEX, hojas georreferenciadas). Implementar:
  - Autenticación server-side real (sesiones/JWT httpOnly, no lógica de auth en el cliente).
  - Los enlaces de "Descargas Autorizadas" deben servirse solo a usuarios autenticados vía backend (no ocultar con CSS/JS — eso no es seguridad real).
  - Sanitizar cualquier formulario (registro, contacto) contra XSS/inyección.
  - HTTPS obligatorio, headers de seguridad (CSP, X-Frame-Options, etc.).
  - Rate-limiting en login/registro.
- **Performance**: imágenes optimizadas/lazy-loaded, CSS/JS minificado, sin librerías pesadas innecesarias, Lighthouse 90+.
- **Animaciones**: modernas y sutiles — transiciones de 120–280ms con easing `cubic-bezier(0.2,0.6,0.2,1)`, encabezado que se oculta/aparece con el scroll, indicadores parpadeantes (halo) en puntos de interés, sin animaciones exageradas ni "bounce".

## Screens / Views (single-page, secciones ancladas)

### 1. Header (sticky)
- Logo FUNDCORSRD (izquierda) + nav (derecha): Inicio, Nosotros (dropdown), Estado Actual, Descargas, Acceso.
- Dropdown "Nosotros": Quiénes Somos, Inscripción, Preguntas Frecuentes, Contactos.
- Comportamiento: fondo blanco sólido en top; al hacer scroll, se vuelve translúcido con blur (`backdrop-filter: blur(16px)`, `background: rgba(250,249,246,0.45)`) y se oculta al bajar / reaparece al subir (`transform: translateY(-100%)` con transición 320ms).
- Menú móvil: hamburguesa que anima a "X" (3 barras con rotate/opacity), abre un drawer/lista vertical.

### 2. Hero (Inicio)
- Fondo blanco, título institucional + descripción + CTA. Texto de marca: "FUNDCORSRD opera y mantiene la red CORS de la República Dominicana" (tono formal, sin exclamaciones).

### 3. Nosotros
- **Quiénes Somos**: texto institucional sobre la fundación.
- **Inscripción**: condiciones de membresía (lista con viñetas verdes, texto justificado a la izquierda) + formulario o CTA.
- **Preguntas Frecuentes**: acordeón (FAQ) expandible.
- **Contactos**: correo, Instagram, WhatsApp — mostrados como filas iguales (incluyendo WhatsApp, mismo tono/peso visual que las demás), sin encabezados redundantes tipo "Correo:"/"Instagram:".

### 4. Estado Actual
- Mapa de estaciones GNSS/CORS (posicionado por debajo del header en scroll — no debe superponerse).

### 5. Descargas
- Enlaces a: Descargas Soluciones FUNDCORSRD, Hojas Topográficas Georreferenciadas, Mapa Manzanero DN (ver carpetas en `uploads/` del proyecto original).

### 6. Acceso (Agrimensores)
- Tarjeta con dos pestañas: **Iniciar Sesión** / **Registrarse**.
  - Iniciar sesión: "Ingrese sus credenciales para acceder a su cuenta."
  - Registrarse: "Complete el formulario para solicitar su registro."
- Al autenticarse, la tarjeta de login/registro se reemplaza por una sección de **Descargas Autorizadas** (contenido restringido — implementar el gating en backend, no en el cliente).
- En el prototipo WordPress esto usaba shortcodes de Ultimate Member (`[um_loggedin]`, `[um_loggedout]`, `[ultimatemember form_id="9"/"10"]`) — en la implementación standalone, reemplazar por un sistema de autenticación propio (ver Seguridad arriba).

## Interactions & Behavior
- Scroll suave a anclas (`scroll-behavior: smooth`, `scroll-margin-top: 84px` para compensar el header sticky).
- Header: oculta/muestra según dirección de scroll; fondo pasa a translúcido con blur pasado cierto scrollY.
- Dropdown "Nosotros": abre/cierra al click, ícono de flecha rota 180°.
- Indicadores "halo" parpadeantes (puntos verdes con anillo pulsante, referencia al logo) en las esquinas de tarjetas destacadas (Quiénes Somos, Inscripción, Acceso, etc.) — rotan de posición entre secciones para variedad visual.
- Tabs de Acceso: click alterna panel visible (login/register) vía `display:none`/`flex`.
- FAQ: acordeón expand/collapse con transición de altura.

## Design Tokens

```css
--green:#116035;          /* Verde Topográfico — acento único */
--green-dark:#0d4a29;      /* hover de green */
--green-soft:#eaf3ee;
--green-soft-2:#f4f9f6;
--carbon:#12291d;          /* texto principal (variante oscura verdosa usada en este prototipo) */
--carbon-soft:#3f5c4c;
--silver:#d1d5db;          /* bordes/divisores únicamente, nunca fills */
--silver-soft:#eef0f2;
--silver-faint:#f7f8f9;
--white:#ffffff;

--font-display: 'Inter', sans-serif;      /* headings, nav, botones */
--font-body: 'Roboto', sans-serif;        /* texto de cuerpo */
--font-mono: 'JetBrains Mono', monospace; /* coordenadas, códigos, valores técnicos */

--radius-sm:4px;  /* inputs, tags */
--radius-md:6px;  /* botones, controles pequeños */
--radius-lg:10px; /* cards, diálogos */
--radius-full:999px; /* toggles/badges */

--shadow-sm: 0 1px 2px rgba(43,43,43,0.05);
--shadow-md: 0 6px 20px rgba(43,43,43,0.06);
--ease: cubic-bezier(0.2,0.6,0.2,1);
```

Nota: la referencia oficial del design system (ver `_ds/` del proyecto) usa `--carbon:#2B2B2B` como gris carbón puro para texto — este prototipo usa una variante verdosa (`#12291d`) para dar más cohesión temática. Confirmar con el cliente cuál es la definitiva antes de producción; por defecto usar la del design system oficial (`#2B2B2B`) si no hay indicación contraria.

Reglas del design system oficial:
- Un solo acento (verde). Gris plata solo para bordes, nunca como fill.
- Sin gradientes, sin texturas, sin fotografía/ilustración decorativa.
- Sin emoji.
- Bordes de 1px hacen el trabajo estructural; sombras solo para elevación real (modales, toasts), muy suaves.
- Fondo oscuro (`--carbon-900`) reservado solo para bandas hero — en este prototipo el hero es blanco (revisar con cliente cuál dirección seguir).

## Assets
- Logo: `assets/logo-fundcorsrd.png` (incluido en este paquete). No recolorear ni redibujar.
- Fuentes: Google Fonts (Inter, Roboto, JetBrains Mono) — considerar auto-hospedar para performance/privacidad en producción.
- Archivos de descarga (PDFs/hojas) referenciados en la sección Descargas: ver carpetas `DESCARGAS SOLUCIONES FUNDCORSRD`, `HOJAS TOPOGRÁFICAS GEORREFERENCIADAS`, `MAPA MANZANERO DN` en el proyecto original (no incluidas en este zip — pedir al cliente los archivos fuente reales).

## Screenshots
Ver `screenshots/` para referencia visual: `01-hero.png`, `02-quienes-somos.png`, `03-inscripcion.png`, `04-mapa-estado-actual.png`, `05-acceso.png`.

## Files
- `reference/fundcorsrd-d1-editorial.html` — versión principal de referencia (la más completa y la última iterada; usar como fuente primaria).
- `reference/fundcorsrd-elementor-completo.html` — misma versión con shortcodes de Ultimate Member inline (referencia de qué contenido va gated tras login).
- Design system oficial (tokens exactos, componentes base): carpeta `_ds/` del proyecto Omelette original — pedir acceso o exportación si Claude Code no tiene el proyecto disponible.

## Next steps sugeridos para Claude Code
1. Set up estructura del proyecto en `/Users/sosa/Dropbox/fundacors-rd` (HTML/CSS/JS vanilla, o un bundler ligero tipo Vite si se prefiere DX moderno sin runtime framework).
2. Recrear estructura y estilos de `fundcorsrd-d1-editorial.html` sección por sección, usando CSS real (no inline) organizado en archivos.
3. Implementar backend de autenticación propio (Node/Express, o el stack que el cliente prefiera) para reemplazar Ultimate Member — sesiones seguras, gating real de descargas.
4. Auditar performance (Lighthouse) y seguridad (headers, CSP, sanitización) antes de lanzar.
