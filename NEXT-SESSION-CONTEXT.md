# Contexto para continuar: ajustes de formato del frontend FUNDCORSRD

## Qué es esta sesión

Esta sesión es **solo para edición visual del frontend**, guiada por capturas de pantalla que el
usuario va a ir pegando. La sesión anterior se quedó sin poder ver imágenes (límite de la
plataforma, no un problema del proyecto), así que se traslada aquí el trabajo que necesita ojos
para terminarse bien.

**No hagas commit, push, ni subas nada a ningún servidor en esta sesión.** El usuario va a volver
a la sesión original para eso — aquí el único objetivo es dejar los cambios listos y verificados
en el preview local. Si terminas algo y no hay más capturas pendientes, dilo y espera.

Proyecto: `/Users/sosa/Dropbox/fundacors-rd` — portal FUNDCORSRD. Frontend estático (HTML/CSS/JS
vanilla + esbuild) para Network Solutions, backend Django para PythonAnywhere. Esta sesión solo
toca `frontend/`.

## Cómo arrancar rápido

```bash
export PATH="/Users/sosa/.nvm/versions/node/v20.20.2/bin:$PATH"
cd /Users/sosa/Dropbox/fundacors-rd/frontend
npm run build
cd dist && npx http-server -p 5500
```

Abrir `http://127.0.0.1:5500/`. Después de cada cambio de CSS/HTML: `npm run build` de nuevo desde
`frontend/` (el `http-server` sirve `dist/` en caliente, solo hace falta reconstruir).

## Estado actual (sin commitear, todo local)

`git status --short` en la raíz del repo debería mostrar estos archivos modificados/nuevos — si no
coincide, algo cambió desde que se escribió este documento, revisar con cuidado antes de asumir:

```
M frontend/package.json
M frontend/src/css/base.css
M frontend/src/css/components/footer.css
M frontend/src/css/components/header-nav.css
M frontend/src/css/components/hero.css
M frontend/src/css/layout.css
M frontend/src/index.html
?? frontend/src/assets/contacts-bg.jpg
?? frontend/src/assets/directiva.jpg
?? frontend/src/assets/footer-bg.jpg
?? frontend/src/assets/hero-bg.jpg
```

(También hay cambios de backend sin commitear — no son parte de esta sesión, no tocarlos.)

## Detalle técnico importante antes de tocar CSS de fondos

- `frontend/package.json`, script `build:css`, tiene `--external:../assets/*` agregado a propósito
  — sin eso, esbuild falla al compilar cualquier `url(../assets/algo.jpg)` en el CSS porque no
  tiene loader configurado para imágenes (el proyecto copia `assets/` aparte, vía
  `scripts/build-copy.mjs`, no a través de esbuild). Si se agrega una imagen de fondo nueva desde
  un CSS dentro de `css/components/`, la ruta correcta es `url(../assets/nombre.jpg)` — un solo
  `../`, porque esbuild bundlea todo a un único `dist/css/main.min.css` y no reescribe esa ruta
  (está marcada como externa a propósito).
- `mask-image` en un elemento afecta **todo su contenido**, incluyendo hijos reales (texto,
  botones) — no solo el fondo. Por eso el fade del hero está en un pseudo-elemento `::before`
  separado (con el fondo ahí) en vez de en `.fcrd2-hero` directamente, que sí tiene el texto real
  encima. Si se necesita otro fondo con fade, replicar ese patrón (pseudo-elemento aparte), nunca
  poner `mask-image` en el contenedor que también tiene contenido real.
- `background-size:100% auto` (mostrar la imagen completa, sin recorte) solo funciona bien si la
  altura de la caja coincide con la altura natural escalada de la imagen. Si la caja es más alta
  (por ejemplo, un `<section>` con mucho contenido debajo, como el de acceso), la imagen — anclada
  arriba o abajo según `background-position` — deja una franja vacía enorme antes de empezar a
  mostrarse, y un `mask-image` de fade calculado sobre el alto TOTAL de la caja puede terminar de
  desvanecerse *antes* de que la imagen siquiera empiece a pintarse. Ya pasó este error una vez
  (sección de acceso, más abajo) — verificar con capturas reales, no solo con los porcentajes en
  la cabeza.

## Assets disponibles en `frontend/src/assets/`

| Archivo | Dimensiones | Uso actual |
|---|---|---|
| `hero-bg.jpg` | 1672×941 | Fondo de `#inicio` (hero) |
| `footer-bg.jpg` | 1774×887 | Pensado para un banner en `#acceso`, ver estado abajo |
| `contacts-bg.jpg` | 1766×286 (banner ancho y bajo) | Fondo de `<footer id="contactos">` |
| `directiva.jpg` | 1400×933 | Foto de la junta directiva, debajo de Misión/Visión en `#quienes-somos` |

Todos ya optimizados (JPEG, no los PNG originales de 1-2MB que mandó el usuario).

## Qué está resuelto y confirmado (no tocar sin que el usuario lo pida)

- **Hero (`#inicio`)**: fondo completo (`hero-bg.jpg`), full-bleed, sin recorte
  (`background-size:100% auto`, `background-position:right top`,
  `min-height:56.3vw` en `.fcrd2-hero` para que quepa entera), se desvanece hacia abajo en su
  propio 40% inferior mezclándose con "Quiénes Somos" (que ya no tiene línea divisoria arriba).
- **Quiénes Somos**: foto `directiva.jpg` debajo de Misión/Visión, ancho completo, sin recortar
  (`height:auto`, no `object-fit:cover`), con borde + sombra simple (`.fcrd2-directiva-img`) — el
  usuario **rechazó explícitamente** un tratamiento de bordes difuminados/mask-image ahí, pidió
  "borde contemporáneo" en su lugar. No revertir a difuminado sin que lo pidan de nuevo.
- **Contactos (footer)**: fondo `contacts-bg.jpg`, `background-size:cover;
  background-position:center`.
- Títulos (`.fcrd2-h2` y el `<h1>` del hero) unificados en tamaño (26px → 22px en el breakpoint más
  chico).
- Espaciado entre título y párrafo (`.fcrd2-h2{margin-bottom}`) aumentado a 26px.
- Márgenes laterales en monitores grandes ampliados (`.fcrd2-section`/`.fcrd2-hero`
  `max-width:1100px` en 1440px+, `1300px` en 1800px+).
- Menú de navegación de escritorio con letra más grande (11.5px → 14px).
- Quitado el stat "±3mm / Precisión geodésica" del hero (quedan 3 columnas, antes 4).
- "Soluciones Red FC" renombrado a "Soluciones de las CORS".
- Gradiente sutil verde-claro→blanco→blanco→verde-claro en `body` (`base.css`) para que las
  secciones sin foto de fondo no corten en seco contra el hero/footer.

## Pendiente / lo que probablemente hay que arreglar con las capturas nuevas

**`#acceso` (sección "Consola RINEX y descargas autorizadas") — sin fondo actualmente, a propósito.**
El usuario pidió ponerle `footer-bg.jpg` como banner arriba, desvaneciéndose hacia arriba contra
"Estado Actual" (el mapa), imagen completa sin recortar, full-bleed. Se intentó tres veces y se
quitó por última vez porque no se pudo confirmar visualmente que quedara bien (la sesión anterior
ya no podía ver capturas). El código actual **no tiene ese fondo** — está limpio, sin
`#acceso::before` ni padding extra. Historial de qué falló antes, para no repetir los mismos
errores:

1. Fondo estirado (`background-size:100% auto`) sobre **toda la altura de la sección**, que
   incluye la tarjeta de login/registro (opaca, blanca, ~500px). Como la imagen se anclaba abajo
   dentro de una caja mucho más alta que ella, la imagen real solo empezaba a pintarse justo antes
   de donde arrancaba la tarjeta — casi nada se veía. Confirmado con muestreo de píxeles
   (comparando tamaño en bytes de recortes de captura entre la "zona de fondo" y una zona en
   blanco conocida) que ahí solo se veía una línea, tal como reportó el usuario.
2. Segundo intento: banner con altura fija en píxeles y `background-size:cover` (para evitar el
   problema anterior). El usuario pidió explícitamente "ponla en full screen, no la cortes de
   ningún lado" — o sea, quiere la imagen completa sin recortar, no un `cover` que recorta.
3. Tercer intento (el más cercano a correcto, pero nunca confirmado visualmente): banner
   independiente con su propia altura fija en `50vw` (exactamente la proporción natural de
   `footer-bg.jpg`, 887/1774), así `background-size:100% 100%` muestra la imagen completa sin
   recortar ni distorsionar por construcción. `#acceso` con `padding-top:calc(50vw + 40px)` para
   que el encabezado/tarjeta queden debajo del banner. Fade de transparente a opaco en el 60%
   superior del banner (no de toda la sección). El código exacto de este intento (para referencia,
   ya no está en el repo, se puede recrear si el usuario confirma que esta dirección estaba bien):

   ```css
   #acceso{position:relative;padding-top:calc(50vw + 40px);}
   #acceso::before{
     content:'';
     position:absolute;
     left:50%;right:50%;
     margin-left:-50vw;margin-right:-50vw;
     width:100vw;
     top:0;
     height:50vw;
     background-image:url(../assets/footer-bg.jpg);
     background-size:100% 100%;
     background-repeat:no-repeat;
     -webkit-mask-image:linear-gradient(to bottom, transparent 0%, black 60%, black 100%);
     mask-image:linear-gradient(to bottom, transparent 0%, black 60%, black 100%);
     z-index:0;
   }
   #acceso > *{position:relative;z-index:1;}
   ```

   Con esto, a 1440px de ancho el banner mide 720px de alto — es bastante grande. Vale la pena
   preguntarle al usuario, mirando la captura real, si ese tamaño se siente demasiado imponente y
   si preferiría volver a aceptar algo de recorte (`cover`) a cambio de un banner más razonable en
   altura, ahora que sí se puede ver el resultado.

**Después de esto**, seguir con lo que el usuario vaya señalando en las capturas nuevas que pegue.

## Preferencias del usuario (aplican también aquí)

- Todo el texto de la página en español correcto, con tildes y ñ (ya se hizo una pasada completa
  de esto en frontend y backend en la sesión anterior — si se agrega texto nuevo, revisar
  ortografía con cuidado).
- Mostrar los cambios en el preview local antes de considerar algo terminado — aquí eso es
  automático ya que esta sesión sí puede ver las capturas.
- Cambios de layout deben funcionar tanto en escritorio como en móvil — probar ambos.
- El usuario prefiere iterar rápido: cambios concretos, verificación visual inmediata con la
  siguiente captura, sin explicaciones largas de más.
