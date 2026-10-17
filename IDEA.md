# Idea

Un viaje completo, de Lima a cualquier pueblo del Perú, tramo por tramo y con su precio,
armado con datos que se consultan en vivo cada vez que alguien pregunta. El ejemplo que define
el producto es ir a Sauce, a la Laguna Azul, sin tour: Lima → Tarapoto en bus o avión, el
tramo local hasta el paradero y el auto compartido que sale cuando llena.

Se usa desde nuestra página o desde ChatGPT o Claude a través de nuestro MCP. La demo compara
el mismo chat sin nuestras herramientas y con ellas.

## Quién tiene el problema y cómo lo resuelve hoy

Alguien en Lima que quiere llegar a un pueblo sin pagar un tour. Hoy junta los tramos a mano:

- el bus en redBus o en la página de la empresa;
- el vuelo en la aerolínea;
- el tramo local preguntando en el paradero o en un blog que puede tener años.

Maps y TuRuta se quedan en la ciudad, redBus vende el bus pero no engancha el colectivo. Nadie
junta los tramos ni el precio total. Un chat general (ChatGPT sin herramientas) contesta con
datos de memoria, sin fuente ni fecha, y a veces inventa paraderos o precios.

## La acción que tiene que poder completar

Escribir a dónde va y en qué fechas, y ver el viaje completo en el orden en que se hace. Cada
tramo muestra:

- de dónde sale;
- cuánto cuesta;
- cuánto demora;
- de dónde sale el dato y cuándo se consultó;
- si alguien que lo hace lo confirmó.

Con eso decide qué tramo comprar ya (con el link a quien lo vende) y cuál todavía no está
confirmado.

## Qué construimos

### 1. Motor de viajes

Recibe destino y fechas y devuelve un itinerario ordenado de tramos. Para cualquier destino:

1. **Planea la cadena de puntos intermedios:** Lima → hub regional → pueblo. Empieza por los
   tramos ya guardados y, si faltan, busca en la web "cómo llegar a X" y un LLM extrae la
   cadena de puntos.
2. **Consulta cada tramo con los conectores.** **Cada consulta refresca los datos** de los
   tramos que toca. Lo guardado sirve de punto de partida, pero no reemplaza la consulta.
3. **Guarda cada tramo encontrado** con su fuente y su fecha, para que la siguiente consulta
   parta de ahí y el grafo de tramos crezca con el uso.
4. **Devuelve el itinerario tramo por tramo (streaming)** a medida que cada uno se resuelve,
   para que la persona no espere a que terminen todos.

### 2. Conectores

Todos implementan la misma interfaz: reciben un tramo (origen, destino, fechas) y devuelven
tramos candidatos con fuente y fecha de consulta.

| Conector | Qué cubre | Con qué |
|---|---|---|
| Búsqueda web + extracción | Cualquier tramo, sobre todo el local: colectivos, autos que salen al llenar, balsas, motos | Tavily y Exa (créditos del evento). Un LLM extrae los tramos de las páginas a un esquema validado. |
| Scrapers dedicados | Los sitios que más pesan: buses interprovinciales y vuelos | Apify (créditos del evento). Solo donde haya un actor que funcione. |
| Confirmaciones del público | Tramos verificados por gente que los hace | Nuestra base de datos |

Para bus y vuelo no copiamos inventario ni vendemos: mostramos salidas y rangos de precio
publicados, y enlazamos a donde se compra.

### 3. Confianza de cada tramo

Cada tramo tiene uno de estos estados, y la página lo muestra siempre:

- **Extraído:** "según <fuente>, consultado el <fecha>".
- **Confirmado:** "confirmado por <nombre> el <fecha>".
- **En disputa:** alguien lo corrigió y hay versiones distintas; se muestran las dos.

Una confirmación se aplica a **una versión concreta de los datos del tramo** (paradero, precio
y tiempo), no al tramo en general. Si una consulta posterior trae valores distintos, se guarda
como versión nueva y el tramo pasa a "en disputa", mostrando la versión confirmada (con quién y
cuándo) junto a la nueva (con su fuente y fecha). Basta una confirmación para pasar a
"confirmado"; una corrección se guarda como versión nueva. Así la regla "nunca confirmado sin
una persona" se cumple aunque los datos cambien. *(Mi decisión.)*

### 4. Confirmación en vivo

En cada tramo, quien lo conoce puede confirmarlo o corregirlo (paradero, precio, tiempo), con
un nombre visible opcional. No hace falta cuenta. Así el público del evento valida las rutas
en vivo, y cada confirmación queda registrada como evidencia de uso.

### 5. Página web (el deploy que ve el jurado)

- **Comparación lado a lado:** a la izquierda el mismo modelo sin herramientas; a la derecha,
  usando las herramientas de Ya Sale. Misma pregunta, mismo modelo, y se ve la diferencia en
  precisión, fuentes y fechas.
- **Vista del itinerario:** tramos en orden, estado de confianza y botón de confirmar o
  corregir.
- **Página de uso:** cantidad de rutas generadas, destinos distintos, confirmaciones y
  personas distintas, con datos reales de la base. Es la evidencia de tracción.

### 6. MCP y CLI

- **Servidor MCP remoto (HTTP)** con las mismas herramientas que usa la página, para
  conectarlo en ChatGPT o Claude: `plan_trip(destination, dates)`,
  `get_leg(origin, destination)` y `confirm_leg(leg_id, …)`.
- **CLI** mínima sobre la misma API, si sobra tiempo.

## Demo (3 minutos)

| Tiempo | Qué se muestra |
|---|---|
| 0:00–0:30 | Problema: llegar a Sauce sin tour obliga a juntar tres tramos a mano |
| 0:30–1:30 | Comparación lado a lado: el chat solo contra el chat con Ya Sale, la misma pregunta |
| 1:30–2:15 | Un destino que pida el jurado o alguien del público, generado en vivo |
| 2:15–2:30 | Alguien confirma o corrige un tramo y el estado cambia en vivo |
| 2:30–3:00 | Arquitectura: motor, conectores, confianza, MCP; y los números de la página de uso |

## Evidencia

- **De que ayuda:** la comparación con y sin herramientas sobre las mismas preguntas. Contamos
  cuántos tramos trae con fuente y fecha, y cuántos datos inventados o desactualizados da el
  chat solo.
- **De uso:** participantes del evento, de todo el Perú, generan la ruta a su pueblo y
  confirman o corrigen la última milla. Se ve en la página de uso y en la base.
- **Lo que todavía no tenemos:** alguien que haga una ruta real con la página y diga si el
  paradero y el precio eran los que usa.

## Qué queda fuera

El viaje de vuelta (solo ida, con fecha de salida; *mi decisión*), cuentas de usuario, compra o
reserva de pasajes, hoteles y tours, el GPS de los buses, la
tarjeta única y el Metropolitano. El tramo dentro de Lima hasta el terminal o el aeropuerto
queda como link a Maps.

## Reglas que no se rompen

- Un tramo nunca aparece como confirmado si ninguna persona lo confirmó.
- Todo precio, horario o paradero lleva su fuente y la fecha de consulta.
- No inventamos cupos ni disponibilidad. Un aviso de "faltan cupos" solo aparece si lo publicó
  la empresa o el cobrador.
- No vendemos ni guardamos tarifas propias. La compra es siempre en el sitio de quien vende.

## Seguridad

- Las claves (LLM, Tavily, Exa, Apify) viven solo en el servidor. La página y el MCP llaman a
  nuestra API, nunca a los proveedores.
- Las rutas de planear, confirmar y el MCP son públicas y anónimas, y cada consulta gasta
  créditos. Por eso llevan límite por IP y un tope de búsquedas y llamadas al LLM por
  consulta.
- El contenido de las páginas que leemos no es confiable: puede traer instrucciones para el
  LLM. El extractor solo devuelve JSON validado contra el esquema de tramo y nunca sigue
  instrucciones que vengan de una página.
- Las confirmaciones también son entrada no confiable. Se guardan tal cual, con su fecha;
  nadie puede borrar las de otro, y no pedimos datos personales.
- El repo es público: nada de claves ni datos de usuarios en el código ni en los avances.

## Decisiones

**Del equipo:**

- Datos en vivo en cada consulta, con todos los conectores posibles.
- MCP para usarlo desde ChatGPT o Claude, y CLI opcional.
- La demo compara un chat sin herramientas con uno usando el MCP.
- Rutas generadas para cualquier destino, que el público prueba y confirma en vivo.
- Búsqueda web más extracción con LLM como conector universal, y Apify para los sitios que
  más pesan, usando los créditos del evento.
- La página web existe porque es el deploy que pide la entrega.

**Mías (se pueden cambiar):**

- **Cara principal de la demo:** la página con la comparación lado a lado.
- **Backend en Python con FastAPI (`uv`):** el motor, los conectores y el servidor MCP en un
  solo servicio, con el SDK oficial de MCP en HTTP.
- **Frontend en Next.js (`pnpm`):** la página.
- **Base de datos:** Postgres administrado, para tramos, confirmaciones e itinerarios.
- **Deploy:** el frontend en Vercel. El backend en Maritime si lo permite (tenemos USD 100 en
  créditos); si no, cualquier servicio de contenedores.
- **Streaming del itinerario** para que la consulta en vivo no se sienta lenta.

## Fuentes de la ruta de ejemplo

- [redBus, Lima a Tarapoto](https://www.redbus.pe/pasajes-de-bus/lima-a-tarapoto)
- [Buscobus, Lima a Tarapoto](https://buscobus.pe/horarios-y-pasajes/lima-a-tarapoto-en-bus/)
- [Laguna Azul, cómo llegar en colectivo](https://tarapoto.net/lugares-turisticos/laguna-azul-sauce/)
- [Apu Samay, colectivo, balsa y moto](https://apusamay.com/como-llegar-a-la-laguna-azul-desde-tarapoto/)
