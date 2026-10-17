# Guía de Hack the Andes — equipo Ya Sale

Todo lo que sabemos del evento en un solo lugar. Fuentes: el
[deck de onboarding](https://hacktheandes.com/deck/onboarding), la
[guía oficial](https://hacktheandes.com/guide) y la CLI `andes` (v0.1.278).
Si algo de acá contradice al servidor (`andes --output json team`, `andes status`),
manda el servidor.

> Este repo es público: acá no van códigos de créditos, contraseñas ni tokens.
> Esos se consultan con `andes credits` y en [hacktheandes.com/wifi](https://hacktheandes.com/wifi).

## Estado del equipo

| | |
|---|---|
| Equipo / proyecto | **Ya Sale** (el proyecto usa el nombre del equipo) |
| Integrantes | Cuisangelo (solo) |
| Track | Movilidad y Transporte (`transport`) — cupo lleno, 7/7 |
| Check-in | Confirmado |
| Repo | https://github.com/cuisangelo/ya-sale |
| Idea del producto | Por definir |

## Fechas clave

**Entrega: domingo 18 de octubre, 09:00** con `andes project submit`.
Se puede (y conviene) enviar antes y corregir después.

Cuando la organización abre la evaluación guarda una copia de la entrega, los links y el log.
Lo que cambies después no llega al jurado.

### Sábado 17

| Hora | Qué |
|---|---|
| 09:00–09:30 | Bienvenida y sponsors (auditorio) |
| 09:30–10:15 | Presentación de Grokbot (auditorio) |
| 10:15–10:30 | Formación de equipos y elección de track |
| 10:30–11:15 | Networking |
| 11:15–14:00 | Building (salas) · 12:00–12:45 AMA de Victor, Path Pilot |
| 14:00–15:00 | Almuerzo |
| 15:00–19:00 | Building |
| 19:00–20:00 | Cena |
| 20:00–00:00 | Building |

### Domingo 18

| Hora | Qué |
|---|---|
| 00:00–09:00 | Dormir o seguir construyendo |
| **09:00** | **Cierre de entregas** |
| 09:00–09:30 | Desayuno |
| 09:30–10:00 | Mensaje de cierre |
| 10:00–13:30 | Demos en vivo (auditorio) |
| 13:30–13:45 | Ganadores |
| hasta 14:00 | Networking y salida |

## Track: Movilidad y Transporte

- **Lima:** transporte público — rutas, conexiones, tiempos y accesibilidad.
- **Regiones:** transporte de pasajeros, conectividad entre localidades, carga y distribución.

Proyectos con software, APIs y datos abiertos; no hace falta hardware.

## Qué hay que entregar

Los cuatro son obligatorios:

1. **URL de deploy** pública y funcionando.
2. **URL de la presentación** (Canva, Google Slides o hecha con código).
3. **URL del repo de GitHub**: https://github.com/cuisangelo/ya-sale
4. **Descripción en Markdown**: el problema, para quién es, cómo funciona y sus limitaciones.

**No cuenta:** localhost, solo slides o pitch, mockups, video grabado.

El deploy tiene que funcionar:

- en una ventana privada, sin tu sesión iniciada;
- sin permisos pendientes ni archivos locales;
- desde la compu de la organización, porque tu laptop no se conecta a la presentación.

Prepará un recorrido de demo que funcione solo con esos links.

```bash
andes --output json project submit \
  --deployment-url https://... \
  --presentation-url https://... \
  --github-url https://github.com/cuisangelo/ya-sale \
  --file ./proyecto.md

andes --output json project submit --presentation-url https://...   # actualiza un solo campo
```

## Avances (log del equipo)

Lo ven los mentores y el jurado, con el autor y la fecha de cada entrada. Publicá un avance
después de una decisión importante, una prueba con usuarios, una demo que funciona o un
bloqueo. Contá qué cambió, por qué y cuál es el siguiente paso. No hace falta narrar cada
commit, y no se publican secretos ni datos personales.

```bash
andes --output json project update --message "..."
andes --output json project update --file ./avance.md
andes project updates   # log completo
andes project           # entrega actual y cantidad de avances
```

## Demo (domingo 10:00–13:30)

Son 3 minutos de demo y 2 de preguntas, en la compu de la organización y con los links que
entregaste. El corte en el minuto 3 es estricto.

| Tiempo | Qué |
|---|---|
| 0:00–0:30 | Problema: a quién le sirve y qué resuelve |
| 0:30–2:30 | Demo en vivo desde la URL pública |
| 2:30–3:00 | Cómo está hecho: arquitectura y decisiones técnicas |
| 3:00–5:00 | Preguntas del jurado |

## Cómo se evalúa

Rúbrica oficial (PDF "Cómo se evalúa a los equipos", entregado en el evento). Coincide con el
deck de onboarding y reemplaza la de la guía web (tracción, técnico y pitch), que quedó
desactualizada.

**Requisitos para que el equipo se evalúe** (si falta uno, no se puntúa): URL pública
desplegada, demo en vivo (slides o video no cuentan) y código en GitHub. Hora límite: domingo
18 a las 09:00.

Cada uno de los 5 jurados pone de 1 a 5 en cada criterio; se multiplica por el peso y se suma.
La nota final es el promedio de los 5. **Máximo: 5,5** (3,75 técnico + 1,25 producto + 0,5 de
bonus).

| Criterio | Peso | 1 | 3 | 5 |
|---|---|---|---|---|
| Complejidad técnica | 30% | Wrapper de una API o CRUD simple | Integra APIs, datos o un modelo con lógica propia | Datos reales, modelos o servicios orquestados, arquitectura no trivial |
| Funciona (en vivo desde la URL) | 25% | Falla en vivo | Corre con datos de juguete | Datos reales y aguanta preguntas fuera del guion |
| Calidad técnica (repo) | 20% | Frágil o con secretos en el repo | Ordenado, con atajos | Maneja errores, casos borde y credenciales |
| Problema e impacto | 15% | Tema genérico | — | Usuario específico y evidencia del problema |
| Claridad | 10% | No se entiende qué hicieron | — | Qué, por qué y qué quedó fuera |

**Bonus por tracción** (se suma encima, no reemplaza lo técnico):

| Tracción | Puntos |
|---|---|
| Sin usuarios fuera del equipo, o sin evidencia | 0 |
| Personas fuera del equipo lo usaron y se ve en registros o datos | +0,25 |
| Uso repetido, volumen visible, lista de espera real o un pago | +0,5 |

La evidencia se muestra **desde el producto**. Capturas solas, cuentas del equipo o tráfico
automatizado no cuentan.

**Desempate:** gana el mayor puntaje en complejidad técnica; si sigue empatado, en "funciona".

## Premios

- **1.º:** S/6,000 · **2.º:** S/2,000 (Chofex), más un viaje al HQ de Chofex y mentoría de StartUPC.
- **Qatom:** 1.º, 12 meses del plan Max; 2.º y 3.º, 7 meses. Además, a cada integrante de esos
  equipos un voucher de 12 meses de Qatom Pro.
- **AtomicMemory:** 1.º, 1 año del plan Max; 2.º y 3.º, 1 año del plan Pro.

## Créditos de sponsors

Se ven con `andes credits`, que muestra los códigos y los pasos de canje. Ninguno se canjea
solo. Vencimientos relevantes: Tavily vale del 17 al 19 de octubre, Lovable hasta el 20 de
octubre a las 17:00 y Zavu se habilita el 18 de octubre.

| Sponsor | Para qué sirve |
|---|---|
| Tavily | Búsqueda web y lectura de páginas para agentes (8,000 créditos) |
| Exa | Búsqueda semántica de páginas y documentos (USD 50) |
| Apify | Scrapers ya hechos (USD 100) |
| Maritime | Hosting de agentes en micro-VMs con disco persistente (USD 100) |
| n8n | Automatización de flujos (1 mes Cloud Pro) |
| Lovable | Generador de apps web con IA (plan Pro) |
| Zavu | API de WhatsApp, SMS, email y voz (3 meses). Dudas en Discord: viktorpy, jullietv, calmizir |
| Qatom | Plan Max por 6 meses: agentes y transacciones ilimitados, hasta 1,000 ítems de catálogo |
| AtomicMemory | Memoria persistente para agentes (5 meses de Pro) |
| Grok | Suscripción de xAI por referido |

Zavu es el más relevante para transporte: le permite al usuario consultar rutas o recibir
alertas por WhatsApp o SMS, sin instalar nada.

## Logística

- **Sede:** pisos 3 y 4 (auditorio y salas). Hay comida, bebidas, energizantes y zonas de silencio.
- **Wi-Fi:** [hacktheandes.com/wifi](https://hacktheandes.com/wifi).
- **Canal oficial:** Discord, [hacktheandes.com/discord](https://hacktheandes.com/discord).
- **Mentores:** 5 en la sala. Jurado: 5.
- **Conducta:** respeto, pedir permiso antes de grabar y reportar situaciones inseguras.
  El acoso, las amenazas o las represalias significan expulsión.

## CLI de referencia

```bash
andes update                    # actualizar CLI y skill antes de empezar
andes checkin --status          # ver si el check-in está confirmado
andes team                      # equipo, integrantes, track y cupos
andes team rename --name "..."  # cambia el nombre del equipo y del proyecto
andes credits                   # beneficios de sponsors
andes project                   # estado de la entrega
andes project update --message "..."
andes project submit ...
```

Para agentes: `--output json` va antes del subcomando, por ejemplo
`andes --output json project submit`.

## Links

- Guía: https://hacktheandes.com/guide
- Deck de onboarding: https://hacktheandes.com/deck/onboarding
- Galería de proyectos: https://hacktheandes.com/projects
- Términos de participación: https://hacktheandes.com/participation-terms
- Discord: https://hacktheandes.com/discord
