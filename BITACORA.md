# Bitácora — Ya Sale

Registro de cambios, decisiones, pruebas y bloqueos del proyecto, de más nuevo a más viejo.
Horas en hora de Lima. Las reglas para escribir acá están en [AGENTS.md](AGENTS.md#bitácora).

Tipos: **Cambio** · **Decisión** · **Prueba** · **Bloqueo** · **Deploy** · **Entrega**.

## 2026-10-17

### 14:10 · Cambio · Planificador de viajes: primero lo guardado, después en vivo

- **Qué:** `TripPlanner`.
  1. Busca cómo llegar y arma la cadena de tramos con Claude.
  2. Emite primero los tramos guardados.
  3. Refresca cada tramo en vivo, en paralelo, con un tope de 8 búsquedas por viaje.
  4. Si el lugar no existe dice "No encontramos cómo llegar…" en vez de inventar.
  5. Si un proveedor falla, ese tramo marca error y los demás siguen.
- **Prueba:** `pytest -q` → 42 passed.

### 14:02 · Cambio · Conectores de búsqueda (delegado a Grok)

- **Qué:** Tavily como fuente principal (`country=peru`, contenido completo) y Exa de respaldo
  si Tavily falla o no trae nada. Tope de búsquedas por viaje (`SearchBudget`) y contenido
  recortado a 12 000 caracteres por página.
- **Quién:** lo escribió Grok 4.7 por `cursor-agent`. Yo revisé el código y agregué que la
  falla de la fuente principal se registre en el log en vez de tragarse en silencio, con un
  test que primero falló.
- **Prueba:** `pytest -q` → 35 passed.

### 13:58 · Cambio · Extractor de tramos con Claude

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

### 13:52 · Cambio · Persistencia de tramos por versiones

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
