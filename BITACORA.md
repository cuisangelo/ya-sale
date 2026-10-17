# Bitácora — Kekero

Registro de cambios, decisiones, pruebas y bloqueos del proyecto, de más nuevo a más viejo.
Horas en hora de Lima. Las reglas para escribir acá están en [AGENTS.md](AGENTS.md#bitácora).

Tipos: **Cambio** · **Decisión** · **Prueba** · **Bloqueo** · **Deploy** · **Entrega**.

## 2026-10-17

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
