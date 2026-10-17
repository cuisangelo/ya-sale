# Bitácora — Ya Sale

Registro de cambios, decisiones, pruebas y bloqueos del proyecto, de más nuevo a más viejo.
Horas en hora de Lima. Las reglas para escribir acá están en [AGENTS.md](AGENTS.md#bitácora).

Tipos: **Cambio** · **Decisión** · **Prueba** · **Bloqueo** · **Deploy** · **Entrega**.

## 2026-10-17

### 18:29 · Cambio · Línea se suma como tercer vendedor de salidas en vivo

- **Qué:** `LineaSource` (`backend/app/connectors/linea.py`) lee la lista de viajes que su propia
  web muestra: `index.aspx/ListarOrigen` y `ListarDestino` dan los terminales, `MostrarItinerario`
  guarda la búsqueda en la sesión y `ECommerce/wf_ListaItinerarios.aspx` devuelve el HTML con cada
  salida (hora, servicio, precio por piso y asientos libres). Cada fila toma el precio más bajo y
  suma los libres de los dos pisos. La lista no trae hora de llegada.
- **Hallazgo:** su servidor guarda en la sesión la primera ruta buscada. Con un cliente compartido,
  la segunda búsqueda devolvía los viajes de la primera (Chiclayo → cualquier destino daba siempre
  3). Por eso cada búsqueda abre su propia sesión.
- **Enlace:** las páginas de resultados y de asientos dependen de la sesión. A un visitante nuevo
  `wf_itinerarioIda.aspx` lo manda a `/index.aspx` (302), así que cada fila enlaza a
  `https://www.linea.pe/`. En Chrome headless con un perfil limpio abre con el formulario de
  compra y Lima en la lista de origen.
- **Pruebas:** 11 tests con fixtures grabados el 17-10 (Lima → Trujillo del 22-10 con 7 viajes y un
  día sin viajes). Mutación: con una sesión compartida entre búsquedas,
  `test_each_search_starts_its_own_session_so_it_never_reads_another_searchs_route` se puso rojo;
  revertido, 11/11. Backend 144/144. En vivo desde local: Lima → Trujillo 7 salidas (09:00
  VIP/ESPECIAL S/80, 54 libres), Lima → Chiclayo 1, Trujillo → Lima 7.

### 18:16 · Decisión · Línea pasa el control de términos y robots

- **robots.txt:** `www.linea.pe/robots.txt` no existe (devuelve su página de 404).
- **Términos:** el único documento de términos es `Terminos_Condiciones_Viaje.pdf`, que regula el
  viaje (DNI, equipaje, postergaciones). No dice nada sobre acceso automatizado, extracción de
  datos ni enlaces. `politicas.aspx` solo lista políticas organizacionales.
- **Cómo se usa:** las mismas llamadas que hace su formulario en el navegador, sin captcha (el
  captcha del sitio solo protege el login de Puntos Linea), sin tokens ni cabeceras firmadas. No
  se entra a la selección de asientos ni se envían datos personales.

### 18:18 · Cambio · Las salidas en vivo dependen del modo de cada tramo, no solo del bus

- **Por qué:** el planner solo pedía salidas para tramos con bus y las emitía siempre como
  `mode: "bus"`. Para sumar vuelos reales (sesión ya-sale-vuelos) y más empresas de bus
  (ya-sale-empresas) hace falta que cada fuente diga qué modo vende.
- **Qué cambia:** `DepartureSource` declara `mode`. Por cada tramo y cada modo del tramo,
  el planner consulta solo las fuentes de ese modo y emite un `leg_departures` por
  `(index, mode)`. Cruz del Sur y Oltursa declaran `"bus"`. La web ya guardaba y mostraba
  las salidas por `(index, mode)`, así que no cambia. Se actualizaron la descripción de
  `plan_trip` en el MCP y `docs/API.md`.
- **Pruebas:** dos tests nuevos (un tramo bus/avión recibe las salidas de cada fuente en su
  modo; una fuente de avión nunca se consulta en un tramo sin avión) fallaron antes del
  cambio; backend 132/132 en verde.

### 18:18 · Cambio · Un enlace de compra solo se muestra si estaba en la página citada

- **Por qué:** Cuiso pidió enlaces que siempre funcionen. El extractor ya exigía que
  `source_url` fuera una de las páginas buscadas, pero aceptaba el `purchase_url` tal como lo
  escribía el modelo, que puede armar un enlace plausible que nunca existió.
- **Qué cambia:** `purchase_url` se conserva solo si aparece literal en el texto de la página
  citada o si es esa misma página. Si no, queda en `null`, y la web cae en la web de la
  empresa o en la página fuente, que existen.
- **Decisiones del mismo bloque:**
  - **redbus.pe queda fuera.** Sus términos (`/info/terminos-y-condiciones`) dicen: "no está
    autorizado a […] crear un vínculo profundo, utilizar, copiar, monitorizar (por ejemplo,
    mediante spider, scrape) […] para ninguna actividad, propósito comercial o competitivo".
    Además, su robots.txt bloquea `/search` y `/seats`.
  - **Cruz del Sur y Oltursa siguen.** Su robots.txt permite todo, y sus términos solo
    prohíben bots para canjear Gift Cards (Cruz del Sur).
  - Se lanzaron las sesiones ya-sale-empresas (operadores directos, con revisión de términos
    por cada uno) y ya-sale-vuelos (fuente de vuelos y salidas por modo).
- **Pruebas:**
  `test_purchase_url_survives_only_when_the_cited_page_contains_it` falló antes de
  implementar (el enlace inventado sobrevivía) y después pasó. Backend 131/131.

### 17:38 · Cambio · El botón del paradero muestra el lugar, no la ruta desde el usuario

- **Pedido de Cuiso:** en Tarapoto → Sauce, "Cómo llegar" abría una ruta de Google Maps
  desde donde está la persona hasta el paradero. Lo que quiere es ver solo el paradero.
- **Qué cambia:** `mapsDirectionsUrl` (`/maps/dir/?destination=`) pasa a ser `mapsPlaceUrl`
  (`/maps/search/?query=`), que abre el lugar con su pin. El botón ahora dice "Ver en el
  mapa".
- **Límite que queda:** el pin es tan bueno como el nombre extraído. Nombres descriptivos como
  "Paradero donde salen los carros a Yurimaguas" no caen en un punto exacto. Para eso hacen
  falta paraderos guardados con su ubicación verificada.
- **Pruebas:** el test del enlace se reescribió y falló antes de implementar; web 35/35 y
  `tsc` en verde.

### 17:32 · Cambio · El MCP devuelve las salidas en vivo con su enlace al asiento

- **Por qué:** la identidad que sostiene Ya Sale frente a "ChatGPT ya lo busca" es el
  inventario en vivo, que no está en la web abierta. Pero `plan_trip` del MCP ignoraba
  `leg_departures`: un ChatGPT o Claude conectado no recibía lo más valioso que tenemos.
- **Qué cambia:** `plan_trip` responde
  `{legs, departures: [{index, mode, departures}], notes}`. Cada salida trae hora, precio,
  asientos libres y `booking_url`. La descripción de la herramienta pide la fecha en
  YYYY-MM-DD, que es lo que permite buscar salidas. `docs/API.md` actualizado.
- **Pruebas:** `test_plan_trip_tool_returns_live_departures_with_their_seat_links` falló antes
  de implementar (el enlace no estaba en la respuesta) y después pasó. Backend 130/130.

### 17:23 · Cambio · Las opciones de kupos, Civa y SKY abren la búsqueda del día del viaje

- **Qué:** `datedLink` en `web/lib/format.ts` reescribe el enlace de una opción cuando el sitio
  acepta el viaje en la URL: kupos y Civa (que corre sobre kupos) abren
  `/es/pasajes-bus/{origen},peru/{destino},peru?date_onward=DD-MM-AAAA`, y SKY abre
  `initial-sale.skyairline.com` con los códigos IATA del tramo y la fecha. Antes llevaban a la
  portada o a una búsqueda con otra fecha. Si un pueblo no tiene aeropuerto conocido, o el sitio
  es otro, el enlace queda igual.
- **Pruebas:** 2 tests nuevos, que fallaron antes de implementar; la web suma 35/35, `tsc` y
  build en verde. En Chrome headless, el enlace de SKY LIM → CUZ del 25-10 listó vuelos
  (04:50 → 06:15, S/ 233,58). El de kupos Lima → Huancayo dejó el buscador lleno, pero headless no
  muestra resultados de kupos; la plantilla la verificó el coordinador en un navegador real.

### 17:21 · Prueba · Oltursa funciona desde Lambda junto a Cruz del Sur

- **Deploy:** PR #14 mergeado (merge `295ece1`); el run 39074527537 terminó con backend, web y
  deploy en verde (22:20:06 UTC).
- **Prueba en producción:** `POST /api/trips` con Lima → Trujillo del 2026-10-22 → 200 en 21 s.
  `leg_departures` trajo 23 salidas intercaladas por hora: 16 de cruzdelsur.com.pe y 7 de
  oltursa.pe (08:00 CDS S/85, 09:05 CDS S/85, 10:00 Oltursa V.RELAX 180 S/80 con 30 asientos,
  11:15 Oltursa S/80, 19:30 CDS S/100…).

### 17:20 · Prueba · El extractor con Sonnet 5.5 funciona en producción

- **Deploy:** el run 39074400710 (`4104e11`) quedó cancelado sin jobs, porque el merge del
  PR #14 entró mientras esperaba. El run 39074527537 (`295ece1`, que incluye `4104e11`) salió
  verde, y Lambda corre `ya-sale:295ece1…`.
- **Viaje real:** `POST /api/trips` Lima → Trujillo 2026-10-24. Eventos: `trip_started`,
  `leg_stored` ×2, `trip_mapped`, `leg_departures`, `leg_refreshed` ×2, `trip_done`, sin
  `leg_error`. Los dos tramos se refrescaron en vivo con Sonnet: bus S/44–55 en 500 min y
  avión (Sky, LATAM) desde S/83 en 70 min. `leg_departures` trajo 16 salidas de Cruz del Sur
  y 7 de Oltursa.

### 17:16 · Cambio · Segundo vendedor de salidas: Oltursa

- **Qué:** `app/connectors/oltursa.py` lee la página pública del día
  (`oltursa.pe/es/viajes/{origen}/{destino}/{AAAA-MM-DD}`), que trae todas las salidas en su
  `__NEXT_DATA__`: hora de salida y llegada, precio "Desde" (`nprecio_desde`), asientos libres
  y tipo de servicio. Los slugs salen de `api.oltursa.com.pe/ws-tienda/api/v1/cities`.
- **Enlace:** la selección de asiento de Oltursa no tiene URL propia (vive en el
  `sessionStorage`), así que cada fila lleva a la lista de ese día. Hora, precio y asientos
  son exactos. `docs/API.md` lo aclara en `booking_url`.
- **Fallar fuerte:** si la página deja de traer `__NEXT_DATA__`, se lanza `OltursaPageChanged`
  y el planner lo registra como fallo de la fuente, en lugar de devolver una lista vacía.
- **Pruebas:** 10 tests contra páginas grabadas (con llegada al día siguiente y cruce de año
  nuevo). Mutación: sin el ajuste de año, falla el test de año nuevo; revertido, pasa. Backend
  127/127, web 33/33. En vivo desde la laptop: Lima → Trujillo el 23-10, 7 salidas; Lima →
  Arequipa, 10.

### 17:16 · Decisión · El extractor y la comparación pasan de Opus 5.5 a Sonnet 5.5

- **Por qué:** la consola de la API marcó USD 11,82 en Claude Opus 5.5 el 17 de octubre. Cada
  tramo y modo manda a Claude hasta 5 páginas de 12 000 caracteres (~15–20 mil tokens de
  entrada), y un viaje hace hasta 12 búsquedas. Opus se eligió por defecto, sin medir si hacía
  falta. Cuiso decidió usar Sonnet 5.5, que cuesta la mitad (USD 2 / 10 por millón de tokens,
  contra 4 / 20).
- **Qué cambia:** `MODEL` en `backend/app/connectors/extractor.py` y en
  `backend/app/compare/service.py`. El resto del código ya cumplía lo que exige Sonnet 5.5:
  no apaga el thinking, no fuerza `tool_choice` y fija `effort: low` explícito.
- **Pruebas:** los tests que fijan el modelo fallaron (2) antes del cambio y después pasaron.
  Suite del backend 119/119, corrida en `docker compose`.

### 17:12 · Prueba · Cruz del Sur funciona desde Lambda: salidas exactas en producción

- **Deploy:** PR #12 mergeado como `845c592`; el run 39073700273 de CI/CD terminó con
  backend, web y deploy en verde (deploy 22:07:58 UTC).
- **Prueba en producción:** `POST https://yasale.cuisangelo.com/api/trips` con Lima → Trujillo
  del 2026-10-22 → 200 en 50 s, con los eventos `trip_started, leg_stored ×2, trip_mapped,
  leg_departures, leg_refreshed ×2, trip_done`. `leg_departures` trajo 16 salidas ordenadas:
  08:00 → 19:50 S/85 46 asientos, 09:05 → 19:50 S/85, 19:30 → 06:45 S/100…
- **Enlace generado desde Lambda:** su id termina en `_3_us` (desde Lima, `_3_pe`). Abierto en
  un Chrome limpio, mostró "Lima - Trujillo · 08:00 - 22 Oct · 46 Libres".
- **Web pública:** `yasale.cuisangelo.com/viaje?o=Lima&d=Trujillo&f=2026-10-22`, en un Chrome
  headless sin sesión, mostró "Salidas del jueves 22 de octubre" con 16 filas, cada una con su
  enlace y logo.
- **Ajuste de la revisión:** si Cruz del Sur rota su clave pública, una búsqueda con 401 vuelve
  a leer `/config` y reintenta una vez; un segundo 401 se registra como fallo de la fuente.
  2 tests nuevos; el backend suma 119/119.

### 17:06 · Decisión · El agente de compra (nivel 2) queda fuera por ahora

- **Qué era:** un agente con computer use que abriera la salida en el sitio del vendedor,
  eligiera asiento, llenara los datos del pasajero y se detuviera antes de pagar.
- **Por qué no:** se probó antes de construir nada y en ningún caso le gana a un buen link.
  - Ya hay link a la salida exacta o a la búsqueda llena: Cruz del Sur (lleva a elegir
    asiento), Inca Rail (URL con fecha y pasajeros, muestra trenes y precios en vivo sin
    cuenta), búsqueda de kupos, Google Vuelos (un link LIM→TRU mostró 10 vuelos de LATAM y
    Sky, desde S/ 206).
  - Otros bloquean la navegación automatizada: PeruRail ("Access Denied" de Akamai en su
    motor de reservas), redbus (403 en la portada y conexión cortada en la ruta) y LATAM (403
    "Por motivos de seguridad…"). No se intentó esquivar ningún bloqueo.
  - Lento para una demo en vivo: la portada de kupos tardó 84,6 s desde Lima; movilbus no
    respondió en 75 s.
  - Pagar en un navegador remoto haría pasar la tarjeta del usuario por nuestro servidor, y
    además muchos vendedores piden cuenta.
- **Medido:** Chromium headless (Playwright) y curl desde Lima, entre 16:45 y 17:05. redbus
  Lima→Trujillo declara 13 operadores y 127 servicios, y no incluye a Cruz del Sur.
- **Queda:** los links por vendedor los hace ya-sale-salidas. El nivel 2 se nombra en el pitch
  como lo que quedó fuera. Los términos de varios vendedores prohíben automatizar, otra razón
  para no hacerlo sin un convenio.
- **Recursos:** no se creó código ni nada en AWS.

### 17:02 · Cambio · Primer vendedor con pasaje exacto: Cruz del Sur

- **Qué:** `app/connectors/cruzdelsur.py` consulta la API de su propia web de venta
  (`one-api.cruzdelsur.com.pe`): lee la clave pública de `/config` en cada arranque (no se
  guarda ni se registra), traduce el lugar a su slug con `/places`, busca y consulta el
  resultado hasta que el estado sea `finished`. Cada salida enlaza a
  `viajes.cruzdelsur.com.pe/purchase/{tripId}/new/A1`, que abre la selección de asiento de esa
  salida sin sesión. Si no atienden el lugar (p. ej. Barranca), devuelve `[]` sin buscar.
- **Prueba en vivo desde la laptop:** Lima → Trujillo el 23-10-2026, 16 salidas (09:05 → 19:50,
  S/85, 45 asientos libres…); Lima → Ica, 61. El enlace de la salida de las 09:05 del 22-10 abrió
  en un Chrome limpio "Lima - Trujillo · 09:05 - 22 Oct · 46 Libres · S/ 85". Ahí nos detuvimos:
  sin datos personales y sin pago.
- **Prueba de la UI:** stream real de producción (Lima → Trujillo) con un `leg_departures`
  armado con esas salidas: la tarjeta muestra "Salidas del viernes 23 de octubre" con 16 filas,
  logo, hora, precio y asientos, sobre "Ver las 10 opciones".
- **Tests:** 8 tests del adaptador contra respuestas grabadas (`tests/fixtures/cruzdelsur`, con
  clave falsa); el backend suma 117/117.
- **Descartados por ahora:** redbus (Akamai y bloqueo de Chromium automatizado), kupos
  (API firmada y cifrada) y PeruRail (Akamai). Oltursa sigue como segundo vendedor.

### 16:55 · Cambio · La tarjeta del tramo muestra "Salidas del <fecha>" con enlace a cada salida

- **Qué:** el reducer guarda las salidas de `leg_departures` por `(index, mode)`, y sobreviven
  a que el tramo se refresque. `HopCard` las lista sobre "Ver las N opciones": logo del sitio que
  vende, hora de salida → llegada (reloj de Lima), precio y asientos libres. Cada fila es un
  enlace al `booking_url` de esa salida. Las opciones de siempre quedan debajo como respaldo.
- **Pruebas:** 5 tests nuevos (reducer, `parseSse`, hora, título con la fecha, asientos).
  Fallaron antes de implementar; ahora la web suma 33/33, `tsc` sin errores y build en verde.
- **Decisión sobre usar el navegador de Claude para kupos:** no sirve para el flujo en vivo,
  porque corre en la sesión de desarrollo y no en Lambda. Un Chrome headless en Lambda tampoco
  conviene: kupos no tiene enlace por salida (depende del `sessionStorage`), en local no cargó
  resultados ni con user agent normal, y pesa memoria, tiempo e IP de datacenter.

### 16:52 · Cambio · Contrato de salidas concretas: `Departure` y evento `leg_departures`

- **Por qué:** hoy cada opción de bus dice "Salidas 5:00 a.m. – 7:30 p.m. · S/20", algo que
  cualquier IA responde. Lo que nos diferencia es llevar al pasaje exacto: una salida concreta
  (empresa, hora, precio, asientos) con el enlace a su selección de asiento.
- **Qué:** `app/departures/domain.py` define `Departure` y el puerto `DepartureSource`; cada
  vendedor será un adaptador nuevo cableado en `build_services` (por ahora no hay ninguno).
  `TripPlanner` consulta las fuentes en paralelo por cada tramo con bus y emite
  `leg_departures` `{index, mode, departures}` ordenado por hora. Si una fuente falla, tarda más
  de 15 s o no encuentra nada, se registra un warning con el vendedor y el motivo, y el viaje
  sigue igual. Una fecha que no es `YYYY-MM-DD` (MCP, `/compare`) omite las salidas sin
  romper el viaje. Documentado en `docs/API.md`.
- **Pruebas:** 109/109 en verde contra Postgres local. Mutación: con el `except Exception`
  cambiado por `except ZeroDivisionError`, fallan los tests de fuente rota y fuente lenta (2);
  revertido, pasan.
- **kupos.pe:** su API de disponibilidad (`api.kupos.pe/api/v3/scheduled_services`) exige
  tokens firmados en el cliente y responde cifrada. No la vamos a eludir; queda solo como
  búsqueda prellenada con la fecha del viaje.

### 16:28 · Cambio · El logo de cada opción es el del sitio al que lleva el clic

- **Problema que vio Cuiso:** en Lima → Barranca la fila "Movil Tours" mostraba el logo de
  Movil Bus, pero abría `buscobus.pe/horarios-y-pasajes/lima-barranca-en-bus/`.
- **Regla nueva:** el enlace va al `purchase_url`; si no hay y la empresa es conocida, a su
  propia web (Movil Bus, Civa, Oltursa, Cruz del Sur, LATAM, SKY, JetSMART, Star Perú,
  PeruRail, Inca Rail); si tampoco, a la página de la ruta de donde se leyó. El logo siempre
  sale del dominio del enlace, así que logo y destino no pueden contradecirse.
- **Procedencia:** cuando el destino no es la fuente del dato, la fila dice
  `www.movilbus.pe · dato de buscobus.pe`.
- **Pruebas:** los tests de `optionLink` y `logoDomain` se reescribieron para la regla nueva.
  Fallaron (2) antes de implementar y después pasaron; la web suma 28/28. `tsc` y build en
  verde. Las webs de las empresas responden 200 a `curl`, salvo LATAM (corta HTTP/2) y Civa
  (403), que bloquean clientes que no son navegador.

### 16:22 · Cambio · Las opciones llevan directo a la ruta y muestran el logo de quien vende

- **Pedido de Cuiso:** al hacer clic en una opción, llegar directo a la compra de esa ruta, y
  poner logos de las empresas o páginas para que la lista no se vea vacía.
- **Clic:** toda la fila es un enlace al `purchase_url` de la opción o, si no hay, a la
  página de la ruta de donde se leyó. Antes solo el dominio chico era clicable. Con datos
  reales de Lima → Tarapoto las fuentes ya son páginas de la ruta, por ejemplo
  `checkmybus.pe/lima-lp/tarapoto-sm` y `kupos.pe/es/pasajes-bus/lima,peru/tarapoto,peru`.
- **Logos:** se muestra el de la empresa cuando la conocemos (LATAM, SKY, JetSMART, Star
  Perú, Cruz del Sur, Oltursa, Civa, Movil Bus, PeruRail, Inca Rail); si no, el del sitio que
  vende. Si no hay logo, salen las iniciales.
- **Decisión:** Cuiso pidió guardarlos de nuestro lado ("en un S3 o algo"). Quedan como
  archivos estáticos en `web/public/logos/` y los sirve el CDN de Vercel: no hace falta
  bucket, IAM ni código de backend. `web/scripts/fetch-logos.mjs` los descarga una vez del
  servicio de favicons de Google y salta los que no existen (404). Bajó 21 de 21.
- **Pruebas:** 4 tests nuevos en `web/lib/format.test.ts`. Fallaron antes de implementar y
  después pasaron; la web suma 28/28. `tsc` y `pnpm build` en verde.

### 15:54 · Deploy · Primer CD a Lambda medido; App Runner pausado; el pull del adaptador falla

- **CD medido:** el run 39068229128 (`5ad2523`) salió verde. Build 18 s con caché,
  actualización de la función 10 s y smoke test con arranque en frío 10 s. Del push a
  producción, 1 min 39 s. Lambda corre `ya-sale:5ad2523…` y `/api/health` responde 200 en
  0,44 s desde el dominio.
- **App Runner:** `pause-service` sobre el servicio `ya-sale`; quedó `PAUSED`. Se reanuda con
  `resume-service` si hace falta volver.
- **Bloqueo:** el run 39068537021 (merge del PR #8) falló al construir. El pull anónimo de
  `public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1` devolvió
  `toomanyrequests: Data limit exceeded`, porque la cuota anónima es por IP y las IPs de los
  runners de GitHub se comparten. El rate limiter en Postgres todavía no está vivo.
- **Arreglo:** el job de deploy inicia sesión en ECR Public antes del build y usa la cuota de
  la cuenta. El rol `ya-sale-github-deploy` suma `ecr-public:GetAuthorizationToken` y
  `sts:GetServiceBearerToken`, aplicado con `infra/github-oidc.sh`.
- `infra/README.md` describe ahora la arquitectura real: web en Vercel, API en Lambda.

### 15:53 · Cambio · Mapa del viaje: los tramos por tierra siguen la carretera

- **Por qué:** cada tramo era una recta entre dos puntos; Lima → Tarapoto cruzaba la sierra en
  diagonal.
- **Decisión:** la geometría sale del router público OSRM, consultado desde el navegador
  (`web/lib/roads.ts`, con un caché por cada par de puntos). Sin cambios en el backend ni key.
  Alternativa descartada por ahora: Google Routes desde el backend. Es más robusta, pero la
  polilínea de Lima → Tarapoto pesa 46k caracteres y habría que simplificarla y cachearla; la
  sesión ya-sale-precios habilitó la API y midió eso.
- **Qué:** tierra = carretera, animada al llegar; avión = arco punteado; lancha = recta
  punteada; tren = recta. Si el router falla, el tramo se dibuja recto con el aviso
  "Sin ruta por carretera: trazo aproximado" y el error queda en consola.
- **Prueba:** `tsc` limpio, `pnpm test` 24/24 (3 nuevos en `roads.test.ts`). Mutación: al
  quitar el `cache.delete` de los fallos, el test del caché se pone rojo, y vuelve a verde al
  restaurarlo. Capturas Playwright con OSRM real: Lima → Tarapoto por la Carretera Central,
  arco punteado del avión al cambiar de pestaña. Con el router bloqueado (503) se ven las
  rectas con el aviso.
- **Estado:** PR #11 abierto, pendiente de merge; todavía no está en producción.

### 15:45 · Deploy · La API pasa de App Runner a AWS Lambda

- **Por qué:** App Runner tardaba unos 10 minutos por deploy. Cuiso pidió deploys rápidos y
  eligió Lambda, después de comparar Lambda contra ECS: Lambda despliega en ~2–3 min, ECS en
  ~5–7 y con balanceador.
- **Cómo:**
  - la misma imagen con el Lambda Web Adapter oficial (0.9.1), que corre uvicorn y transmite
    SSE con Function URL `RESPONSE_STREAM`;
  - función `ya-sale-api` en las subredes privadas y el security group del conector, así que
    sigue llegando al RDS privado;
  - 2 GB, 300 s de timeout y concurrencia reservada de 10;
  - pool de Postgres de 4 conexiones por instancia, para no pasar las ~80 del RDS.
- **Medido en la Function URL:**
  - en frío, 23,7 s (la primera llamada tras una imagen nueva);
  - en caliente, 0,8 s;
  - un viaje real Cusco → Aguas Calientes empezó a transmitir en 0,6 s y terminó en 32 s, con
    `trip_mapped` y tramos por modo, es decir el contrato nuevo del PR #5;
  - `POST /mcp` → 200.
- **Cambio de tráfico:** Vercel ahora reenvía `/api/*` y `/mcp` a la Function URL.
- **CD:**
  - compara `main` contra la imagen que corre Lambda y actualiza el código de la función;
  - el rol de GitHub solo puede subir a ECR y actualizar `ya-sale-api`.
- **Límite de viajes:** pasa a Postgres en el PR #8 (sesión ya-sale-precios), porque Lambda
  corre varias instancias.
- **Antes, en el camino:**
  - el backend del PR #5 nunca se había desplegado, porque las corridas pendientes se
    reemplazan entre sí;
  - se repromovió en Vercel la web anterior, se desplegó el backend a mano y se corrigió el CD
    para comparar contra lo que está vivo.
- **App Runner:** queda como respaldo hasta confirmar Lambda en producción.

### 15:40 · Deploy · Carga viva de la vista de viaje en producción

- PR #9 mergeado a las 15:39 (`66b38b2`). Vercel quedó `success` a las 15:40.
- **Verificado en `yasale.cuisangelo.com/viaje`:** responde 200 y el chunk
  `page-1f608adbdc73e756.js` trae las frases nuevas ("Partiendo el viaje en tramos",
  "Seguimos en eso") y la barra de progreso ("Tramos actualizados").

### 15:38 · Cambio · Vista de viaje: carga que se nota viva

- **Por qué:** mientras el backend arma la cadena de tramos solo se veía "Armando tu viaje…",
  y cada tramo pendiente era una línea gris; no quedaba claro si seguía procesando.
- **Qué:**
  - antes de `trip_started`: franja textil que se va tejiendo, frases que siguen los pasos
    reales del planner (buscar cómo llegar, leer guías, partir en tramos, transbordos),
    contador de segundos y tarjetas + mapa en esqueleto;
  - cada tramo pendiente: esqueleto de Pasaje/Viaje y frases propias del modo; cuando se
    acaban queda "Seguimos en eso…" con el contador corriendo;
  - indicador en vivo con barra de progreso tejida k de N, punto que late en las tabs que
    siguen buscando, totales "calculando…" pulsando y entrada animada de los datos;
  - todo se apaga con `prefers-reduced-motion`.
- **Prueba:** `tsc --noEmit` limpio, `pnpm test` 21/21. Build estático servido con un SSE
  simulado (plan de 9 s, tramos llegando a los 13, 17 y 22 s) y capturas con Playwright en
  1280 px y 390 px en cada fase, sin errores de consola. Las capturas encontraron la barra
  vacía (relleno `<span>` inline) y el contador partido en mobile; ambos corregidos.

### 15:22 · Deploy · Web en Vercel, API en App Runner: yasale.cuisangelo.com en vivo

- **Por qué:**
  - el deploy completo tardaba unos 20 minutos (19:51 → 20:11 UTC): la imagen con la web y
    App Runner, que tarda unos 10 minutos por actualización con salida por VPC;
  - CloudFront quedó bloqueado: AWS pide verificar la cuenta, lo que requiere un caso de
    soporte.
- **Elegido:** Cuiso eligió la opción A, la web en Vercel.
- **Cómo queda:**
  - la web (export estático) se sirve desde Vercel, en el proyecto `ya-sale`, conectado al
    repo, así que cada push a `main` la despliega;
  - `web/vercel.json` reenvía `/api/*` y `/mcp` a App Runner, un solo origen y sin CORS;
  - las slides se copian a `/pitch/` en el build.
- **Dominio:** `yasale.cuisangelo.com` pasa al proyecto de Vercel, con certificado automático
  porque el DNS ya vive ahí. Se borró el CNAME que apuntaba a App Runner.
- **Verificado en `yasale.cuisangelo.com`:** `/`, `/pitch/` y `/api/health` → 200. En
  `ya-sale.vercel.app`, las cuatro pantallas, `/og-image.png`, `/api/usage` y `POST /mcp` →
  200, y un viaje real Lima → Paracas por SSE a través del proxy completó (`trip_started`,
  `leg_refreshed`, `trip_done`).
- **Backend:**
  - la imagen ya no construye la web, solo Python;
  - se despliega solo si cambia `backend/`, el `Dockerfile` o `infra/`;
  - el build usa la caché de capas de GitHub Actions.
- **Ajuste:** con el framework en modo Next.js, Vercel aplicaba la redirección de barra final
  antes de los rewrites (`/api/health` → 308 → 404). Se configuró como sitio estático
  (`outputDirectory: out`).

### 15:01 · Cambio · /mcp sin barra final

- **Bug:** lo encontró la sesión de landing en producción. `POST /mcp` respondía 405, y solo
  `/mcp/` funcionaba; la web estática montada en `/` atrapaba la ruta sin barra.
- **Arreglo:** un middleware ASGI mínimo trata `/mcp` como `/mcp/`. No es una redirección,
  porque algunos clientes MCP no siguen redirecciones en un POST.
- **Prueba:** el test reproduce el caso de producción (web montada más `POST /mcp`); falló con
  405 antes del arreglo. `pytest -q` → 75 passed.

### 14:58 · Cambio · Pitch mergeado, slides en /pitch/ y certificado del dominio

- **PR #2 del pitch, mergeado por Cuiso:** `pitch/proyecto.md` (texto de entrega), el guion
  de demo de 3 minutos, 8 slides en estilo textil y el post de LinkedIn.
  - En la revisión se corrigió una afirmación: la pantalla no muestra las dos versiones de un
    tramo en disputa; la API sí las guarda.
  - La imagen ahora copia `pitch/slides` a `/pitch/`.
- **Dominio:** el certificado falló (`create_failed`) porque los CAA de `cuisangelo.com`
  solo autorizaban a DigiCert, Let's Encrypt, Google y Sectigo. Se agregó
  `CAA 0 issue "amazon.com"` sin quitar los demás. Falta reasociar el dominio cuando el
  servicio deje de actualizarse.
- **Sesión `ya-sale-landing` (`4e17a12b`):** rediseña la landing y va a llevar las tipografías
  dentro del repo, porque un build falló al bajarlas de Google Fonts.

### 14:51 · Deploy · GOOGLE_MAPS_API_KEY disponible en producción

- **Contexto:** la sesión ya-sale-precios (ahora a cargo de la UX del itinerario) necesita la
  variable nueva `GOOGLE_MAPS_API_KEY` (Geocoding API, solo servidor, proyecto GCP
  `ya-sale-hta`).
- **Orden acordado** para no romper producción, porque App Runner rechaza un parámetro de SSM
  que no existe:
  1. la clave en SSM;
  2. la clave en los secretos de `release.sh`;
  3. recién entonces el PR de la UX.
- **Hecho:** pasos 1 y 2. `infra/secrets.sh` también la sube.
- **Pipeline:** el CI ya no cancela corridas de `main`, solo de PRs, porque una de `main`
  puede estar a mitad de un deploy.

### 14:48 · Deploy · Dominio yasale.cuisangelo.com

- **Pedido:** Cuiso lo pidió como URL principal del producto.
- **Hecho:** dominio asociado al servicio de App Runner. En el DNS de Vercel se crearon, con
  la CLI (`vercel dns add`):
  - un CNAME `yasale` que apunta a `ibiarhyx7y.us-east-1.awsapprunner.com`;
  - los dos CNAME de validación del certificado de ACM.
- **Verificación:** `dig` contra 1.1.1.1 resuelve los tres.
- **Pendiente:** que AWS valide el certificado. Las slides irán en `/pitch/` cuando se mergee
  el PR del pitch.

### 14:45 · Deploy · Ya Sale en producción (AWS App Runner)

- **URL:** https://ibiarhyx7y.us-east-1.awsapprunner.com (imagen `42e53fc`).
- **Prueba de humo:** `/api/health` → `{"ok":true}`, `/` → 200, y `/viaje/`, `/comparar/`,
  `/uso/` y `/mcp/` → 200.
- **Aceptación del spec:** `POST /api/trips` Cusco → Aguas Calientes en producción devolvió
  2 tramos, cada uno con fuente y fecha. El bus trae precio (S/35); el tren, no.
- **Problemas resueltos en el camino:**
  - el login de Docker contra ECR chocaba con el llavero de macOS → configuración temporal
    sin el helper;
  - pnpm 12 en la imagen rechazó rollup 4.64.9, publicado hace horas → se respeta la regla:
    rollup fijado en 4.64.7, pnpm 10.29.3 fijado y `minimumReleaseAge` de 24 h en todos lados.
- **Merge del PR #1 de precios:** Cuiso lo mergeó; mi merge lo bloqueó el sistema de permisos
  (requiere revisión humana). En las 8 rutas de demo, los tramos con precio pasaron de 5/12 a
  10/11; suite completa: 74 passed.

### 14:45 · Cambio · CI/CD con GitHub Actions y OIDC

- **CI:** en cada push y PR, tests del backend (con Postgres) y de la web (vitest y build).
- **CD:** en cada push a `main`, si el CI pasa, construye la imagen, la sube a ECR y corre
  `infra/release.sh` (actualizar App Runner, esperar `RUNNING` y prueba de humo).
- **Seguridad:** sin claves de AWS en GitHub. El rol `ya-sale-github-deploy` se asume por
  OIDC solo desde `main` de `cuisangelo/ya-sale`; solo puede subir la imagen `ya-sale` y
  actualizar ese servicio. Lo crea `infra/github-oidc.sh`.

### 14:30 · Cambio · Web con las cuatro pantallas (delegada a Grok)

- **Qué:** Next.js con export estático.
  - Pantallas: inicio, itinerario en vivo por SSE, comparación y uso.
  - Componentes: Franja, Logo, LegCard, StatusBadge, ModeIcon y LiveIndicator.
  - Estilo: tokens del textil andino.
- **Quién:** lo escribió Grok 4.7 por `cursor-agent`.
- **Revisión:**
  - usa exactamente los eventos y endpoints de `docs/API.md`;
  - sin Tailwind, sin HTML inyectado, sin `localStorage` ni `console.log`;
  - `pnpm vitest run` → 5 passed y `pnpm build` exporta las 4 páginas.
- **Integración local:** el backend sirve la web y la API desde el mismo origen. `/`,
  `/viaje/`, `/comparar/`, `/uso/`, `/api/health`, `/api/usage` y los SVG responden 200.

### 14:20 · Decisión · Dos sesiones paralelas de Claude

- **`ca039a8c` · ya-sale-precios** (rama `feat/ya-sale-precios`): que más tramos vuelvan con
  precio, más un script que precarga 8 rutas de demo.
- **`76acd583` · ya-sale-pitch** (rama `docs/ya-sale-pitch`): `proyecto.md` para la entrega,
  guion de demo de 3 minutos, slides en estilo textil y post de LinkedIn.
- **Reglas comunes:** cada sesión delega lo mecánico a Grok, abre un PR a `main` y no toca la
  bitácora, para evitar conflictos; sus avances se registran acá al mergear. Esta sesión
  revisa la web de Grok y hace el deploy.

### 14:17 · Prueba · Primer viaje real de punta a punta (local)

- **Consulta:** `POST /api/trips` Cusco → Aguas Calientes, con Tavily, Exa y Claude reales,
  contra el backend en Docker.
- **Resultado:** `trip_started`, 2 `leg_refreshed` y `trip_done`.
  - Bus Cusco → Ollantaytambo: 125 min, primer bus 03:00 y último 19:00, con link de compra
    de redBus. Fuente: redbus.pe.
  - Tren Ollantaytambo → Aguas Calientes: sale de la Estación de Ollantaytambo, 90 min.
    Fuente: cuscoperu.com.
- **Criterio de aceptación:** cumplido; cada tramo tiene `source_url` y `fetched_at`.
- **Pendiente:** esta vez ninguno de los dos tramos trajo precio.
- **Ajuste:** `compose.yaml` suma valores de desarrollo para `FINGERPRINT_SALT` y
  `TEAM_FINGERPRINTS`; la configuración falló a propósito porque faltaban.

### 14:16 · Prueba · Créditos de los sponsors: configurados y útiles

- **Probado:** `scripts/probe_providers.py` con las claves reales, sobre tres viajes (Tarapoto
  → Sauce, Cusco → Aguas Calientes, Iquitos → Nauta). Exit 0.

| Proveedor | Latencia | Resultados .pe | Con precio en soles |
|---|---|---|---|
| Tavily | 1,2–1,6 s | 4 de 15 | 1 de 15 |
| Exa | 3,4–4,1 s | 5 de 15 | 3 de 15 |
| Claude Opus 5.5 | 6,4 s | — | extrajo 1 tramo con precio (Tarapoto → Sauce) |

- **Conclusión:** Exa trae más páginas con precio, así que conviene buscar en los dos en
  paralelo en vez de usar Exa solo de respaldo.
- **Secretos:** las claves quedaron en SSM (`/ya-sale/*`) con `infra/secrets.sh`, junto al
  `DATABASE_URL` de la base privada, que ya está `available`.

### 14:05 · Decisión · Infraestructura AWS: base privada con NAT

- **Pedido:** Cuiso pidió toda la infraestructura en AWS, con la mejor relación
  calidad-precio.
- **Descartado:** abrir el Postgres a internet (la opción más barata). El sistema de permisos
  lo bloqueó por debilitar la seguridad, y con razón.
- **Elegido:**
  - RDS privado, alcanzable solo desde App Runner por un conector VPC;
  - NAT gateway para la salida a Tavily, Exa y Claude (unos USD 1,1 por día);
  - secretos en SSM.
- **Scripts:** `infra/setup.sh`, `infra/secrets.sh` y `infra/deploy.sh`. Detalle en
  `infra/README.md`.

### 13:58 · Cambio · Comparación y servidor MCP

- **Comparación:** `POST /api/compare` hace la misma pregunta al mismo modelo (Opus 5.5) dos
  veces: sin herramientas y con la herramienta `plan_trip` de Ya Sale. Los contadores
  (fuentes, fechas, confirmados) salen de los tramos que devolvió la herramienta, no del texto.
- **MCP:** servidor en `/mcp` (SDK `mcp` v2, `MCPServer`, HTTP sin estado) con las
  herramientas `plan_trip`, `get_leg` y `confirm_leg`. Probado por HTTP con un dominio que no
  es localhost.
- **Prueba:** `pytest -q` → 59 passed.

### 13:55 · Cambio · API en vivo, confirmaciones y uso

- **Viajes en vivo:** `POST /api/trips` transmite el viaje por SSE (`trip_started`,
  `leg_stored`, `leg_refreshed`, `leg_error`, `no_route`, `trip_done`).
- **Confirmar y corregir:** `POST /api/legs/{id}/confirmations` responde 409 "Ya confirmaste
  este tramo." si repetís; `POST /api/legs/{id}/corrections` crea una versión confirmada.
- **Uso:** `GET /api/usage` cuenta viajes, destinos, personas y tramos confirmados desde la
  base, sin contar las huellas del equipo.
- **Guardas:**
  - huella anónima: sha256 con sal de la IP y el user-agent, recortado a 16 caracteres;
  - 6 viajes por minuto por persona;
  - la IP nunca se loguea.
- **Prueba:** `pytest -q` → 52 passed.

### 13:53 · Cambio · Planificador de viajes: primero lo guardado, después en vivo

- **Qué:** `TripPlanner`.
  1. Busca cómo llegar y arma la cadena de tramos con Claude.
  2. Emite primero los tramos guardados.
  3. Refresca cada tramo en vivo, en paralelo, con un tope de 8 búsquedas por viaje.
  4. Si el lugar no existe dice "No encontramos cómo llegar…" en vez de inventar.
  5. Si un proveedor falla, ese tramo marca error y los demás siguen.
- **Prueba:** `pytest -q` → 42 passed.

### 13:50 · Cambio · Conectores de búsqueda (delegado a Grok)

- **Qué:** Tavily como fuente principal (`country=peru`, contenido completo) y Exa de respaldo
  si Tavily falla o no trae nada. Tope de búsquedas por viaje (`SearchBudget`) y contenido
  recortado a 12 000 caracteres por página.
- **Quién:** lo escribió Grok 4.7 por `cursor-agent`. Yo revisé el código y agregué que la
  falla de la fuente principal se registre en el log en vez de tragarse en silencio, con un
  test que primero falló.
- **Prueba:** `pytest -q` → 35 passed.

### 13:49 · Cambio · Extractor de tramos con Claude

- **Qué:** `LegExtractor` con Claude Opus 5.5 (`messages.parse` y salida validada con
  Pydantic, effort `low`). Extrae tramos de las páginas encontradas y arma la cadena de
  puntos de un viaje.
- **Protecciones:**
  - cada página va en un cerco `<untrusted_page>` con nonce, y el prompt dice tratarla como
    datos;
  - se descartan los tramos con precios fuera de (0, 5000] soles, duraciones fuera de 1–4320
    min o una URL de fuente que no está entre las páginas dadas;
  - si Claude rechaza, devuelve vacío.
- **Prueba:** `pytest tests/test_extractor.py` → 7 passed. Se verificó en el código del SDK
  1.15.0 que `output_format` se combina con `output_config`.

### 13:47 · Cambio · Persistencia de tramos por versiones

- **Qué:** `LegRepository` sobre Postgres.
- **Versiones:** un dato equivalente solo actualiza `fetched_at`; un cambio material crea una
  versión nueva, y la confirmada nunca se sobrescribe.
- **Confirmaciones:** una persona (huella) confirma una versión una sola vez. Una corrección
  crea una versión ya confirmada.
- **Prueba:** `pytest tests/test_leg_repository.py` → 6 passed.
- **En paralelo:** Grok arma la web y los conectores de búsqueda; reviso y commiteo lo que
  devuelvan.

### 13:45 · Cambio · Reglas de confianza de los tramos

- **Qué:** el dominio de tramos en `backend/app/legs/domain.py`.
- **Cuándo un dato nuevo es "otro dato":**
  - los rangos de precio no se tocan;
  - la duración cambia más de 25%;
  - el paradero normalizado es distinto.

  Si los precios se solapan, por ejemplo S/12 contra S/10–15, no hay disputa.
- **Estados:** "confirmado" solo si una persona confirmó; "en disputa" si después de lo
  confirmado llegó un dato materialmente distinto.
- **Prueba:** `pytest tests/test_leg_domain.py` → 11 passed.

### 13:44 · Cambio · Esqueleto del backend

- **Qué:** FastAPI con configuración que falla si falta cualquier variable requerida (nombra
  todas las que faltan), Postgres 16 en `compose.yaml` y el esquema con las tablas `legs`,
  `leg_versions`, `confirmations` y `trips`.
- **Prueba:** `docker compose run --rm backend uv run pytest -q` → 5 passed.
- **Contrato:** el contrato entre backend y web quedó fijado en `docs/API.md`.

### 13:40 · Decisión · Spec del MVP, plan de implementación y deploy en AWS

- **Plan:** `docs/superpowers/plans/2026-10-17-ya-sale-mvp.md`, en 10 tareas:
  1. esqueleto;
  2. dominio de tramos;
  3. persistencia;
  4. extractor;
  5. búsqueda;
  6. planificador;
  7. API;
  8. comparación y MCP;
  9. web;
  10. deploy.
- **Deploy:** en la cuenta AWS del perfil `default` (región `us-east-1`), con App Runner, RDS
  Postgres y ECR, en un solo contenedor que sirve la API, el MCP y la web. Reemplaza a
  Vercel y Maritime.
- **Corrección:** las horas de las entradas entre 13:08 y 13:33 se ajustaron a las de sus
  commits; antes estaban adelantadas.

Spec (contrato del MVP):

- **Goal:** una persona escribe origen, destino y fecha y ve su viaje en el Perú tramo por
  tramo, en cualquier modo. Cada tramo lleva fuente, fecha y estado, y se refresca en vivo. Lo
  mismo vía MCP desde ChatGPT o Claude, más la comparación y la página de uso.
- **I/O:**
  - Entrada web: `POST /api/trips {origin, destination, date}` (SSE).
  - Entrada MCP: `plan_trip(origin, destination, date)`.
  - Salida: tramos con modo, puntos, precio, duración, `source_url`, `fetched_at`, estado y
    versión.
  - Otros endpoints: `POST /api/legs/{id}/confirmations` y `GET /api/usage`.
- **Invariants:**
  - Nunca "confirmado" sin una confirmación humana sobre esa versión.
  - Todo dato lleva `source_url` y `fetched_at`.
  - Un cambio material crea una versión nueva y marca "en disputa", sin sobrescribir la
    versión confirmada.
  - El uso sale de la base, no de constantes.
- **Security:**
  - Claves solo en el servidor, validadas al arrancar.
  - Límite por huella y tope de búsquedas y llamadas al LLM por viaje.
  - Páginas no confiables: el extractor solo devuelve JSON validado.
  - Sin datos personales; nunca se loguean claves ni la IP en claro.
- **Acceptance:** `uv run pytest -q` en verde, y `curl` a `POST /api/trips` en el deploy
  devuelve al menos 2 tramos con `source_url` y `fetched_at`.
- **Out of scope:** cuentas, compra, vuelta, hoteles, GPS, tarjeta única. CLI y Apify solo si
  sobra tiempo.

### 13:33 · Decisión · Pantallas del MVP aprobadas

- **Aprobadas:** inicio, itinerario con refresco en vivo, comparación lado a lado y uso en
  vivo.
- **Único cambio pedido:** los inputs del inicio se veían oscuros. Pasan a fondo claro con
  borde color hilo.
- **En el repo:**
  - descripción de cada pantalla en `design/PANTALLAS.md`;
  - mockup de referencia en `design/pantallas-mockup.html`.
- **Siguiente paso:** plan de implementación.

### 13:30 · Decisión · Logo final: inti de franjas, hecho a mano

- **Descartado:** el tawa inti qocha de centro en cuatro ("se ve raro, muy perfecto").
- **Elegido:** el rombo de hebras original, con acabado artesanal:
  - bordes con temblor;
  - hebras variables;
  - textura de fibra (filtro SVG).
- **Respaldo:** en los tejidos Q'ero el inti se teje como franjas en rombo (Bard Graduate
  Center).
- **En el repo:** `design/textil/logo-inti.svg` y `franja.svg`. Con esto se cierra la identidad
  y se pasa a las pantallas.

### 13:27 · Decisión · Logo tawa inti qocha y franja de urdimbre

- **Por qué:** el inti escalonado y la franja de crucecitas seguían leyéndose como pixeles a
  tamaño chico.
- **Variantes comparadas:** hebras, puntada y faja. Cuiso elige "rombo de hebras" y pide
  asegurar que sea peruano.
- **Verificación en fuentes:**
  - El rombo dividido en cuatro (tawa inti qocha) es un motivo peruano desde Nazca y Wari
    hasta los Q'ero de hoy (Silverman-Proust, *Anthropologica* PUCP).
  - El tejido andino es de cara de urdimbre.
- **Ajustes:**
  - centro del rombo en cuatro cuartos (q'olle y añil);
  - hebras verticales;
  - triángulos qocha en la franja.
- **En el repo:** `design/textil/logo-tawa-inti.svg` y `franja.svg`.

### 13:26 · Decisión · Tareas chicas a Grok 4.7 por Cursor

Para ahorrar uso de Claude, las tareas mecánicas se delegan con
`cursor-agent -p --model grok-4.7-medium`. Las decisiones, la arquitectura y la seguridad quedan
en el agente principal, y lo que devuelva Grok se verifica antes de commitear. Queda en
`AGENTS.md`.

### 13:21 · Decisión · Estilo final: tejido vectorial con toques de hilo

- **Pixel art descartado:** a Cuiso no le gustó.
- **Variantes modernas comparadas:**
  - D, tejido vectorial;
  - A, geometría plana;
  - B, hilo;
  - C, bloques.
- **Elegida:** D con toques de B.
  - De D: inti escalonado como logo, franjas de manta y barra lateral del color de cada medio.
  - De B: el zigzag del mayu une los tramos, los íconos van en círculo de contorno y las
    fuentes en monoespaciado.
- **En el repo:** los SVG pixelados y su generador se reemplazan por los vectoriales en
  `design/textil/`. El README tiene la paleta, los estados y la anatomía de la tarjeta de
  tramo.

### 13:15 · Cambio · Recursos de la identidad textil

- **Qué:** `design/textil/` con 4 motivos (inti, chakana, ch'aska y mayu), una franja tejida y
  7 íconos de transporte (bus, combi, colectivo, mototaxi, avión, tren y lancha). Todos son
  SVG pixel a pixel, más el generador y la paleta de tintes naturales.
- **Rol de cada motivo:** inti es el destino y el logo, chakana el transbordo, ch'aska un tramo
  confirmado y mayu el camino.
- **Origen:** diseños propios inspirados en el pallay, sin copiar el de ninguna comunidad.
- **Referencias:** Awamaki y el Centro de Textiles Tradicionales del Cusco (tintes).
- **Siguiente paso:** Cuiso revisa el detalle en el compañero visual.

### 13:11 · Decisión · De cualquier punto a cualquier punto, todos los modos

- **Qué:** el producto deja de ser "de Lima a un pueblo" y pasa a ser de cualquier origen a
  cualquier destino del Perú. Cubre todos los tipos de transporte:
  - bus interprovincial, avión y tren;
  - colectivo, combi y cúster;
  - bus urbano, Metropolitano y Metro;
  - mototaxi y moto;
  - lancha, bote, peque-peque y balsa.
- **Por qué:** Cuiso sentía muy acotado el ejemplo de Tarapoto → Sauce, que pasa a ser un
  ejemplo entre varios.
- **Efecto en `IDEA.md`:** el tramo urbano ya no queda fuera.

### 13:11 · Decisión · Dirección visual: textil andino

Entre chicha, paradero, combi, costa-sierra-selva y retablo, Cuiso elige el textil andino.
Pide detallarlo con recursos propios o encontrados.

### 13:08 · Decisión · Alcance, latencia y modelo por defecto

Cuiso pidió avanzar sin responder estas tres preguntas, así que quedan las propuestas por
defecto. Se pueden cambiar.

- **Orden de recorte:**
  1. motor con búsqueda y extracción;
  2. itinerario con confirmar;
  3. comparación lado a lado;
  4. MCP;
  5. página de uso;
  6. Apify;
  7. CLI.

  El MVP para publicar en LinkedIn son los cinco primeros.
- **Latencia:** lo guardado se muestra al instante y cada tramo se refresca en vivo en
  pantalla, marcando cuáles ya se actualizaron.
- **LLM:** Claude Opus 5.5 en todo, con los créditos de API del plan Max de Cuiso (organización
  de Console vinculada). Falta el login de `ant`.

### 13:04 · Decisión · El producto se llama Ya Sale

"Kekero" era temporal. "Ya Sale" es lo que grita el cobrador aunque la combi no salga: es
jerga peruana, lo reconoce cualquiera y resume el tramo informal que resuelve el producto. La
búsqueda no encontró ninguna app de transporte en Perú con ese nombre.

- Equipo en Hack the Andes renombrado a "Ya Sale"; el track sigue siendo `transport`.
- Repo de GitHub: `cuisangelo/Kekero` pasa a `cuisangelo/ya-sale`.
- Docs actualizados. Las entradas anteriores de esta bitácora conservan el nombre viejo.

### 12:59 · Decisión · Rúbrica oficial confirmada

El PDF "Cómo se evalúa a los equipos" confirma la rúbrica del deck:

- 75% técnico: complejidad 30%, funciona 25%, calidad 20%.
- 25% producto: problema e impacto 15%, claridad 10%.
- Hasta +0,5 de bonus por tracción, mostrada desde el producto.

Desempate por complejidad técnica. La rúbrica de la guía web queda descartada. Se actualiza
`GUIDE.md`.

### 12:49 · Decisión · Todo va directo a `main`

Cada cambio se commitea y se pushea a `main` en fast-forward, sin PR. Los PRs quedan solo para
cuando trabajan sesiones en paralelo. Queda escrito en `AGENTS.md`.

### 12:47 · Decisión · Pendiente: proveedor de LLM

Ninguno de los créditos del evento cubre un LLM general (solo el referido de Grok). Hay que
elegir proveedor y clave antes de construir el extractor y la comparación. Lo define Cuiso.

### 12:46 · Decisión · La idea pasa a ser un motor de viajes en vivo

- **Qué:** `IDEA.md` deja de ser un viaje curado a Sauce y pasa a ser un motor para cualquier
  destino. Refresca cada tramo en cada consulta, mide la confianza de cada tramo, ofrece un
  MCP para ChatGPT o Claude y una demo que compara el chat solo contra el chat con Kekero.
- **Por qué:** la versión curada tenía poca complejidad técnica (40% de la nota), casi ninguna
  tracción posible en 24 horas y funcionaba para un solo destino.
- **Conectores:**
  - Tavily y Exa, más un LLM que extrae los tramos, como conector universal;
  - Apify para los sitios que más pesan;
  - las confirmaciones del público.
- **Stack (propuesta, se puede cambiar):** FastAPI con `uv`, Next.js con `pnpm`, Postgres,
  Vercel y Maritime.
- **Evidencia:** commit `a054aae`, rama `docs/idea-v2`.

### 12:37 · Decisión · Primera idea: Lima → Sauce sin tour

Bus o avión hasta Tarapoto, tramo local hasta el paradero y auto compartido. El tramo local
solo se afirma si alguien que lo hace lo confirmó. Evidencia: commit `805a158`.

### 11:43 · Cambio · Reglas para agentes

Se agregan `AGENTS.md` (prioridades, git, secretos, CLI `andes`, verificación, arquitectura,
SOLID, código siempre en inglés) y `CLAUDE.md`, que lo importa. Se mergea a `main`.
Evidencia: commits `721ff5e` y `defc63f`.

### 11:39 · Cambio · Guía del evento

Se agrega `GUIDE.md`, que junta el deck de onboarding, la guía web y la CLI: entrega el domingo
a las 09:00, cuatro requisitos, demo de 3 minutos, rúbrica y créditos. Queda anotado que la
rúbrica del deck y la de la guía web no coinciden. Evidencia: commit `a950a81`.

### 11:35 · Cambio · Repo renombrado

`cuisangelo/hacktheandes` pasa a llamarse `cuisangelo/Kekero`; GitHub redirige la URL vieja.

### 11:04 · Decisión · Equipo Kekero, track Movilidad y Transporte

El equipo se crea como CUISO y se renombra a Kekero, con un solo integrante. Track `transport`;
después de elegirlo, el cupo se llenó (7/7). Check-in confirmado.
