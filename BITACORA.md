# Bitácora — Ya Sale

Registro de cambios, decisiones, pruebas y bloqueos del proyecto, de más nuevo a más viejo.
Horas en hora de Lima. Las reglas para escribir acá están en [AGENTS.md](AGENTS.md#bitácora).

Tipos: **Cambio** · **Decisión** · **Prueba** · **Bloqueo** · **Deploy** · **Entrega**.

## 2026-10-17

### 13:45 · Decisión · Estilo final: tejido vectorial con toques de hilo

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

### 13:30 · Cambio · Recursos de la identidad textil

- **Qué:** `design/textil/` con 4 motivos (inti, chakana, ch'aska y mayu), una franja tejida y
  7 íconos de transporte (bus, combi, colectivo, mototaxi, avión, tren y lancha). Todos son
  SVG pixel a pixel, más el generador y la paleta de tintes naturales.
- **Rol de cada motivo:** inti es el destino y el logo, chakana el transbordo, ch'aska un tramo
  confirmado y mayu el camino.
- **Origen:** diseños propios inspirados en el pallay, sin copiar el de ninguna comunidad.
- **Referencias:** Awamaki y el Centro de Textiles Tradicionales del Cusco (tintes).
- **Siguiente paso:** Cuiso revisa el detalle en el compañero visual.

### 13:20 · Decisión · De cualquier punto a cualquier punto, todos los modos

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

### 13:20 · Decisión · Dirección visual: textil andino

Entre chicha, paradero, combi, costa-sierra-selva y retablo, Cuiso elige el textil andino.
Pide detallarlo con recursos propios o encontrados.

### 13:10 · Decisión · Alcance, latencia y modelo por defecto

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
