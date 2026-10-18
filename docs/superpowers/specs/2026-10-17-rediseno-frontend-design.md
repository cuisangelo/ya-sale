# Rediseño del frontend de Ya Sale: foto protagonista, identidad propia

Diseño acordado con Cuiso el 17 de octubre de 2026, por la tarde. Los mockups aprobados están
en [2026-10-17-rediseno/](2026-10-17-rediseno/): `inicio.html` y `viaje.html`. `rojo.html`
compara los rojos; se eligió el carmín. En `inicio.html`, las tarjetas de identidad B y C de
arriba quedaron descartadas; vale el inicio completo de abajo.

## Intención

Ya Sale tiene que sentirse **moderno, funcional y usado de verdad**. Hoy se ve antiguo: el fondo
beige, los motivos textiles peruanos y muchos tamaños de letra lo recargan. Lo que importa es la
información útil para quien viaja (cuánto cuesta, cuánto demora, de dónde sale, dónde comprar).
También que cada viaje y cada visita al inicio se vean distintos, con la foto del destino.

El jurado de Hack the Andes abre la URL pública el domingo 18 a las 09:00. Lo que ve primero es
el inicio y la vista de viaje.

## Objetivos

1. **Identidad propia y moderna:** fondo blanco, un solo acento carmín (`#C8102E`), tinta casi
   negra y grises suaves. Sin motivos culturales.
2. **Foto protagonista por destino:**
   - cada viaje muestra arriba una foto real de su destino, con su crédito;
   - el inicio muestra la foto del destino de la última búsqueda registrada.
3. **Inicio que cambia:**
   - la sección "Lo último que la gente buscó" lista las últimas búsquedas registradas, cada una
     con su foto;
   - al tocar una se abre ese viaje.
4. **Vista de viaje útil arriba:** una tarjeta flotante con el precio mínimo, la duración total,
   los tramos y transbordos, la primera salida y el estado de carga en vivo.
5. **Tipografía disciplinada:**
   - una sola familia;
   - tres tamaños en todo el sitio: 40, 18 y 14 px;
   - la jerarquía se marca con peso y color.
6. **Animaciones con sentido:**
   - zoom lento de la foto;
   - la tarjeta flotante que sube;
   - los tramos que aparecen al llegar;
   - la carga viva que ya existe (frases, contador, barra, esqueletos) pasada al estilo nuevo.

## No objetivos

- Rediseñar `/comparar` y `/uso`: solo heredan los tokens nuevos (colores, tipografía, fondo
  blanco), sin cambiar su estructura.
- Cambiar el flujo SSE del viaje, el planner, la extracción o las confirmaciones y correcciones.
- Rehacer las slides del pitch.
- Modo oscuro.

## Anti-objetivos (fallaría aunque "funcione")

- Que se confunda con Booking (azul) o con Airbnb (rojo rosado `#FF385C` + foto grande). El
  carmín y el logo propio lo separan; no se usa rosado.
- Que vuelva a verse recargado: nada de franjas, motivos, más de un color de acento ni tamaños
  de letra fuera de la escala.
- Una foto que no corresponde al destino, o un mapa o escudo en lugar de una foto.
- Una foto sin crédito: las licencias de Wikimedia lo exigen.
- Texto ilegible sobre la foto.
- Que el inicio muestre una sección vacía o datos inventados presentados como reales.

## Restricciones

- **Plazo:** domingo 18 de octubre a las 09:00 (America/Lima). Lo que no esté en `main` y
  desplegado para entonces no cuenta.
- **Stack que se conserva:**
  - Next.js con export estático (`output: "export"`) en Vercel;
  - CSS propio (`web/styles/*.css` y CSS Modules);
  - Leaflet para el mapa;
  - API FastAPI en AWS Lambda detrás del proxy `/api/*` de Vercel;
  - `pnpm` y `uv`.
- **Sin dependencias nuevas de UI ni frameworks CSS.** La fuente se autoaloja como `.woff2` en
  `web/app/fonts/`, igual que las de hoy.
- **Sesiones paralelas** tocan `web/` ahora mismo: hoy `HopCard.tsx` sumó salidas con logo y
  link de compra. El rediseño se construye sobre lo que esté en `main` y se integra por PR.
- Reglas del repo ([AGENTS.md](../../../AGENTS.md)):
  - fail loud;
  - adapters para servicios externos;
  - dominio sin I/O;
  - tests unitarios de dominio y casos de uso;
  - bitácora en cada paso.

## Lo que decidió Cuiso

- **Dirección visual:** foto protagonista (opción B), con UI blanca y datos en una tarjeta
  flotante.
- **La foto cambia en cada viaje y el inicio también cambia.**
- **Inicio:** se muestran las últimas búsquedas que se registraron, sin ventana de tiempo, para
  que nunca quede vacío. Tocar el backend está bien.
- **Sin cultura peruana en el diseño:** se quitan la franja, la chakana, el mayu, la chaska y el
  fondo beige. Identidad propia.
- **Acento:** carmín `#C8102E`. Contraste con blanco de 5,9:1, pasa AA a 14 px.
- **Pocos tamaños de letra.**
- **Fuera del inicio:** la franja de números de uso y el bloque de "cómo funciona", porque no le
  aportan nada al usuario.
- **Alcance:** inicio y viaje se rediseñan completos; `/comparar` y `/uso` heredan los tokens.
- **Vista de viaje:** aprobada como está en `viaje.html`.

## Lo que decidí yo (Claude), revisable

- **Logo:**
  - ruta curva que llega a un punto, en blanco sobre un cuadrado carmín de esquinas redondeadas;
  - nombre en minúsculas: "ya sale";
  - SVG inline; reemplaza el `logo-inti.svg`.
- **Familia tipográfica:** Inter, autoalojada en `.woff2`, con licencia OFL. Pesos 400, 600, 700
  y 800.
- **Tokens (reemplazan `web/styles/tokens.css`):**
  - `--acc: #C8102E` (acción, precio, en vivo);
  - `--acc-soft: #FBE7EA` (fondos de estado en vivo);
  - `--ink: #111114`;
  - `--mute: #6B6B76` (texto secundario, 5,3:1 sobre blanco);
  - `--line: #ECECF0`;
  - `--soft: #F6F6F8`;
  - fondo `#FFFFFF`.
  - Los colores por modo (`tab-land`, `tab-air`…) desaparecen; el modo se distingue por ícono y
    nombre. En el mapa, el trazo de los tramos por tierra va en carmín, el avión y la lancha
    punteados y el tren en tinta.
- **Escala tipográfica:**

  | Tamaño | Peso | Para qué |
  |---|---|---|
  | 40 px | 800 | Solo para el título del hero |
  | 18 px | 700–800 | Destacados: campos del buscador, precios, título de tramo, nombres de sección |
  | 14 px | 400/600/700 | Todo lo demás, incluidos créditos, fuentes y metadatos (en `--mute`) |

  Nada de 11, 12, 13, 21, 22, 30 ni 34 px. En celular el título baja a 32 px: es la única
  excepción, y existe solo para que quepa.
- **Íconos de modo:** se reemplazan los SVG textiles de `public/textil/` por íconos de línea
  simples, monocromos en `--ink` (bus, avión, tren, auto, combi, mototaxi y lancha).
- **Carga de fotos de destino** (`web/lib/photos.ts`): es un adapter del cliente, como
  `roads.ts`. Validado a mano contra 7 destinos el 17/10:
  1. pide a es.wikipedia el artículo con el nombre exacto (`prop=pageimages|coordinates`,
     `redirects=1`, `origin=*`);
  2. lo acepta solo si las coordenadas del artículo están a menos de 25 km del punto
     geocodificado;
  3. si no, prueba `<nombre> (Perú)`;
  4. si no, usa `generator=geosearch` en un radio de 10 km alrededor del punto y toma la primera
     página cuya imagen no sea SVG, mapa, escudo, bandera ni logo
     (`/\.svg$|mapa|map|localizaci|location|escudo|bandera|flag|coat|logo/i`);
  5. el crédito sale de commons.wikimedia.org (`prop=imageinfo&iiprop=url|extmetadata`,
     `iiurlwidth=1280`): `Artist` (HTML a texto plano), `LicenseShortName` y la página del
     archivo;
  6. guarda en caché por par de coordenadas, en memoria y en `localStorage` con `try/catch`.

  Las fotos van sin key y sin backend. En la prueba, 5 de 7 destinos dieron foto por nombre y 2
  por cercanía; en ningún caso salió un mapa.
- **Sin foto:** si los pasos fallan, o si Wikipedia no responde, el hero usa un fondo degradado
  de carmín a tinta, con el nombre del destino y sin crédito. Es un estado diseñado y visible, no
  un hueco; el error queda en `console.error`.
- **Cada viaje guarda su destino resolvido (decidido por Cuiso tras la revisión).** `trips`
  suma tres columnas que se escriben cuando el planner ubica el destino del último tramo de la
  cadena (el `TripMapped`):
  - `resolved_destination` (texto);
  - `destination_lat`;
  - `destination_lng`.

  En `schema.sql` va como `ALTER TABLE trips ADD COLUMN IF NOT EXISTS …`. Un viaje que terminó en
  "No encontramos cómo llegar", o cuyo destino no se pudo ubicar, queda con esas columnas en NULL.
  Las 24 búsquedas que ya existen no se rellenan: el inicio arranca con pocas tarjetas, y Cuiso
  lo aceptó.
- **Endpoint nuevo `GET /api/trips/recent`:** responde
  `[{origin, destination, place, at, lat, lng}]`, donde:
  - `origin` y `destination` son lo que la persona escribió (con eso se arma el link
    `/viaje/?o=…&d=…` y se escribe el título "A → B");
  - `place`, `lat` y `lng` son el destino resolvido (con eso se busca la foto).

  Las búsquedas se filtran y ordenan así:
  - solo viajes con `resolved_destination` no nulo, es decir, búsquedas que dieron una ruta;
  - en orden descendente por fecha;
  - deduplicadas por el par origen–destino escrito, sin distinguir mayúsculas (queda la más
    reciente);
  - máximo 8;
  - excluye las huellas del equipo, igual que `/api/usage`;
  - nunca devuelve `fingerprint`.

  Si no hay ninguna, la sección no se muestra y el hero del inicio usa el estado "sin foto" con
  el claim. Es un estado vacío honesto: no se inventan búsquedas.
- **Secciones del inicio (decidido por Cuiso tras la revisión):** quedan solo estas, en este
  orden:
  1. hero con la navegación;
  2. buscador flotante;
  3. "Lo último que la gente buscó";
  4. una sección compacta "Para agentes", con la URL del MCP y el botón de copiar
     (`McpUrl`); el link "Para agentes" del menú apunta a su ancla;
  5. un pie mínimo con el link al repo de GitHub.

  Se eliminan `RouteCards`, con sus fotos en `public/landing/`; `SampleTrip`; "¿Tu pueblo está
  al final del camino?"; `UsageProof`; y el bloque de pasos. En el menú, "Comparar" y "Uso real"
  apuntan a `/comparar` y `/uso`.
- **Hero del inicio:** usa la primera búsqueda de `/api/trips/recent`, con la etiqueta "Última
  búsqueda: A → B, hace N min".
- **Tarjetas de búsquedas recientes:** muestran foto, "A → B" y "hace N min". No muestran los
  medios de transporte, porque el endpoint no los conoce.
- **Vista de viaje:**
  - una pastilla "A → B · fecha · Cambiar" en el hero vuelve al inicio con el formulario
    precargado;
  - "Primera salida" en la tarjeta flotante es la salida más temprana **del primer tramo** con
    el modo elegido, mostrada como "hora · empresa" (por ejemplo "12:00 · Cruz del Sur"). Si el
    primer tramo no tiene salidas, el campo no se muestra. Nunca se toma de un tramo posterior,
    porque haría pasar el bus del segundo tramo por la salida del viaje. `Departure` no tiene
    paradero, así que no se inventa uno.
- **Favicon y `og-image.png`:** se rehacen con el logo nuevo.
- **Animaciones:**

  | Elemento | Animación |
  |---|---|
  | Foto | Zoom de 115 % a 100 % en 16 s |
  | Tarjeta flotante | Sube 10 px con fundido en 400 ms |
  | Tramos | Sube 10 px con fundido en 500 ms, escalonado |
  | Tarjetas del inicio | Al pasar el mouse suben 3 px y ganan sombra |

  Todo se apaga con `prefers-reduced-motion`.

## Spec (contrato)

```
Goal:        Ya Sale se ve moderno y propio: foto del destino en cada viaje y en el inicio, datos útiles arriba, carmín como único acento.
I/O:         trips gana resolved_destination/destination_lat/destination_lng, escritos al ubicar el último tramo;
             GET /api/trips/recent → [{origin, destination, place, at, lat, lng}] (≤8, solo viajes con ruta);
             foto: (nombre, lat, lng) → {url, autor, licencia, página} | null, desde Wikipedia/Commons en el cliente.
Invariants:  - toda foto mostrada lleva su crédito (autor + licencia + link);
             - /api/trips/recent nunca devuelve huellas, IPs ni nombres; excluye al equipo y los viajes sin ruta;
             - un viaje sin ruta (no_route o destino sin ubicar) deja resolved_destination en NULL, nunca un valor inventado;
             - el texto sobre la foto siempre va sobre el degradado oscuro (contraste ≥ 4,5:1);
             - solo 40/18/14 px en todo el CSS (32 px solo en el título móvil);
             - el SSE del viaje, las confirmaciones y las correcciones se comportan igual que antes.
Security:    /api/trips/recent es público y de solo lectura: expone el origen y destino escritos de viajes que sí dieron
             una ruta, más el destino resolvido; React escapa el texto. No toca secretos. Wikipedia/Commons se llaman
             desde el navegador sin credenciales; el HTML de "Artist" se reduce a texto plano antes de mostrarlo.
Acceptance:  cd backend && uv run pytest -q   (incluye tests nuevos de /api/trips/recent);
             cd web && pnpm exec tsc --noEmit && pnpm test   (incluye tests de photos.ts);
             grep -RnoE 'font-size: *[0-9]+px' web/styles web/app | grep -vE ': *(40|18|14)px|32px' → vacío;
             capturas Playwright de / y /viaje en 1280 y 390 px; en vivo: curl /api/trips/recent → 200 con ≤8 items.
Out of scope: /comparar y /uso (solo tokens), backend del planner, MCP, slides del pitch, modo oscuro.
```

## Lo que queda a criterio de quien construya

- Cómo se parte el CSS: reescribir `app.css` y `landing.module.css`, o separarlos por componente.
- Los íconos de modo concretos, siempre que sean monocromos y de línea.
- La forma exacta del estado "sin foto", dentro del degradado carmín a tinta.
- El orden de los PRs, siempre que cada uno deje `main` desplegable.
