# Ya Sale

**Tu viaje por el Perú, tramo por tramo, con fuente y fecha.** Escribes de dónde sales, a dónde
vas y cuándo, y Ya Sale arma el viaje completo en el orden en que se hace, en cualquier modo:
bus, avión, tren, colectivo, combi, mototaxi, lancha o balsa. Cada tramo dice de dónde sale,
cuánto cuesta y cuánto demora, de qué página salió el dato, cuándo se consultó y si alguien que
hace la ruta lo confirmó.

Track **Movilidad y Transporte** · equipo Ya Sale (Cuisangelo) · Hack the Andes 2026.

- **Demo:** https://yasale.cuisangelo.com *(pendiente: falta validar el certificado del dominio)*
- **Respaldo directo:** https://ibiarhyx7y.us-east-1.awsapprunner.com
- **Slides:** https://yasale.cuisangelo.com/pitch/ *(pendiente)*
- **Repo:** https://github.com/cuisangelo/ya-sale

## El problema

Llegar a un lugar que no conoces en el Perú, sobre todo fuera de la ciudad, obliga a armar el
viaje a mano. Para ir de Lima a la Laguna Azul (Sauce, San Martín) sin tour hacen falta cuatro
tramos y cuatro fuentes:

1. el bus en redBus o en la página de la empresa, o el vuelo en la aerolínea, hasta Tarapoto;
2. el mototaxi hasta el paradero;
3. el auto colectivo a Sauce, que sale cuando se llena;
4. la balsa o la lancha, que se averiguan preguntando en el paradero o en un blog que puede
   tener años.

redBus vende el bus pero no conecta con el colectivo ni con la lancha. Maps y TuRuta cubren
parte de la ciudad. Nadie junta los tramos de todos los modos con su precio. Un chat general
sin herramientas responde de memoria, sin fuente ni fecha, y a veces inventa paraderos o
precios.

## Para quién

Para cualquier persona que tiene que llegar a un lugar del Perú que no conoce, cuando el viaje
mezcla transporte formal e informal: turistas nacionales que van sin tour, gente que visita a
su familia en provincia y quien se muda o viaja por trabajo a otra región. También sirve para
moverse dentro de Lima en combi o Metropolitano.

## Cómo funciona

1. **Planea la cadena de tramos.** Busca en la web "cómo llegar de X a Y" con Tavily y Exa en
   paralelo, y Claude extrae de esas páginas los puntos intermedios y el modo de cada tramo.
2. **Muestra primero lo guardado.** Si un tramo ya se había consultado, aparece de inmediato
   con la fecha de esa consulta.
3. **Refresca cada tramo en vivo.** Cada tramo se busca de nuevo, en paralelo, y Claude extrae
   paradero, operador, precio, duración, horario y link de compra. El resultado se valida
   contra un esquema estricto.
4. **Transmite el viaje por streaming (SSE).** Cada tramo llega a la pantalla apenas se
   resuelve, sin esperar a los demás.
5. **Guarda cada tramo con su fuente y su fecha,** así cada consulta deja lista la siguiente.

Cada tramo tiene uno de tres estados, y la pantalla siempre lo muestra:

- **Extraído:** "según <fuente>, consultado el <fecha>".
- **Confirmado:** una persona que hace la ruta confirmó esa versión exacta (paradero, precio y
  tiempo). Nunca aparece como confirmado si nadie lo confirmó.
- **En disputa:** después de lo confirmado llegó un dato distinto. El tramo se marca en
  disputa y se guardan las dos versiones: la API las devuelve (`GET /api/legs/{id}`), pero la
  pantalla del itinerario todavía muestra solo la versión vigente con la etiqueta. Un dato es
  distinto si los rangos de precio no se tocan, si la duración cambia más de 25% o si el
  paradero es otro.

Quien conoce un tramo puede confirmarlo o corregirlo sin crear una cuenta. Cada confirmación
queda registrada y suma a la página de uso.

### La comparación

`/comparar` hace la misma pregunta al mismo modelo (Claude Opus 5.5) dos veces: sin
herramientas y con la herramienta `plan_trip` de Ya Sale. Los contadores de fuentes, datos con
fecha y tramos confirmados salen de los tramos que devolvió la herramienta, no del texto del
modelo.

### MCP para ChatGPT o Claude

El mismo motor se expone como servidor MCP remoto en `/mcp` (HTTP), con las herramientas
`plan_trip(origin, destination, date)`, `get_leg(leg_id)` y
`confirm_leg(leg_id, version_id, display_name?)`.

## Arquitectura

```
Navegador / ChatGPT / Claude
        │
        ▼
AWS App Runner ── un contenedor: FastAPI (API + SSE) + servidor MCP + web estática (Next.js)
        │ conector VPC
        ├──► RDS Postgres 16 privado: tramos, versiones, confirmaciones, viajes
        └──► NAT gateway ──► Tavily · Exa · Claude
```

- **Backend:** Python 3.12, FastAPI y `uv`, organizado por dominio (`legs/`, `trips/`,
  `connectors/`, `compare/`, `usage/`, `api/`). Las reglas de confianza son lógica pura en
  `backend/app/legs/domain.py`, sin I/O.
- **Conectores:** Tavily y Exa como fuentes de búsqueda detrás de una misma interfaz, y un
  extractor con Claude Opus 5.5 que solo devuelve salida estructurada validada con Pydantic.
- **Persistencia por versiones:** un dato equivalente solo actualiza la fecha de consulta; un
  cambio material crea una versión nueva y la versión confirmada nunca se sobrescribe.
- **Web:** Next.js exportada como sitio estático y servida por el mismo backend, con la
  identidad textil andina del proyecto (`design/textil/`).
- **Tests:** 74 tests con `pytest` sobre el dominio, la persistencia, el extractor, el
  planificador, la API y el MCP, más los tests y el build de la web (`vitest`).
- **CI/CD:** GitHub Actions corre los tests del backend (con Postgres) y de la web en cada push
  y PR. Cada push a `main` con el CI en verde construye la imagen y la despliega en App Runner.
  GitHub no guarda claves de AWS: el deploy asume un rol por OIDC que solo puede subir esa
  imagen y actualizar ese servicio.

### Seguridad

- Las claves de Tavily, Exa y Claude viven solo en el servidor (AWS SSM) y la configuración
  falla al arrancar si falta alguna. La web y el MCP llaman a nuestra API, nunca a los
  proveedores.
- Las páginas que leemos no son confiables: cada una va cercada con un nonce, el modelo las
  trata como datos y se descartan los tramos con precios fuera de (0, 5000] soles, duraciones
  fuera de 1–4320 minutos o una fuente que no está entre las páginas leídas.
- Las rutas son públicas y cada consulta gasta créditos, así que hay un tope de 8 búsquedas por
  viaje y de 6 viajes por minuto por persona.
- No hay cuentas ni datos personales. Cada persona se cuenta con una huella anónima (hash con
  sal), y la IP nunca se guarda ni se loguea.
- La base de datos no es accesible desde internet.

## Lo que ya medimos

Prueba de los proveedores con las claves reales sobre tres viajes (Tarapoto → Sauce, Cusco →
Aguas Calientes, Iquitos → Nauta):

| Proveedor | Latencia | Resultados .pe | Con precio en soles |
|---|---|---|---|
| Tavily | 1,2–1,6 s | 4 de 15 | 1 de 15 |
| Exa | 3,4–4,1 s | 5 de 15 | 3 de 15 |
| Claude Opus 5.5 | 6,4 s | — | extrajo 1 tramo con precio (Tarapoto → Sauce) |

Exa trae más páginas con precio, así que se busca en los dos a la vez.

Primer viaje de punta a punta (Cusco → Aguas Calientes, con los proveedores reales): bus Cusco →
Ollantaytambo, 125 min, primer bus 03:00 y último 19:00, con link de compra de redBus, y tren
Ollantaytambo → Aguas Calientes, 90 min. Cada tramo llegó con su fuente y su fecha de consulta.
Ninguno de los dos trajo precio.

Después de ajustar el planificador para quedarse con el candidato que trae precio y buscar el
precio cuando falta:

- en las 8 rutas de demo, los tramos con precio pasaron de 5 de 12 a 10 de 11 (Postgres local,
  con la base vacía);
- en producción, el mismo viaje Cusco → Aguas Calientes trajo el bus con precio (S/35) y el tren
  sin precio.

## Limitaciones

- **Los precios no siempre aparecen.** Muchas páginas no publican la tarifa del tramo local, y
  preferimos dejar el precio vacío antes que inventarlo.
- **Solo precios en soles.** PeruRail e Inca Rail publican en dólares, y esos precios se
  descartan. El S/15 que puede aparecer en el tren a Aguas Calientes es la tarifa del Tren
  Local, que es solo para residentes.
- **Los datos son tan buenos como las páginas que existen.** Para un pueblo pequeño puede no
  haber ninguna página útil; en ese caso Ya Sale dice "No encontramos cómo llegar…" en vez de
  inventar una ruta.
- **Una consulta en vivo tarda varios segundos** por la búsqueda y la extracción. El streaming
  muestra cada tramo apenas está listo, y lo guardado aparece primero.
- **Las confirmaciones son anónimas.** Una persona puede confirmar una versión una sola vez,
  pero sin cuentas no podemos verificar quién es.
- **Solo ida,** con una fecha de salida.

## Qué queda fuera o todavía es idea

- La compra o reserva de pasajes: siempre se enlaza al sitio de quien vende.
- El viaje de vuelta, las cuentas de usuario, los hoteles y tours, el GPS en tiempo real y la
  tarjeta única de pago.
- **Idea, no construido:** scrapers dedicados para buses, vuelos y trenes (Apify), una CLI
  sobre la misma API y consultas o alertas por WhatsApp o SMS (Zavu).
- **Pendiente para la entrega:** el certificado de `yasale.cuisangelo.com`, las slides en
  `/pitch/` y la evidencia de uso fuera del equipo en `/uso`.
