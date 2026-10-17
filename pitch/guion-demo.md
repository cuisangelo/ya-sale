# Guion de la demo · 3 minutos

Domingo 18, a partir de las 10:00, en la compu de la organización y solo con los links
entregados. El corte del minuto 3 es estricto. Todo lo que diga en voz alta tiene que poder
mostrarse en pantalla.

## Antes de subir (09:30–09:55)

- [ ] `curl -s https://yasale.cuisangelo.com/api/usage` responde 200, y anotar las cuatro cifras.
- [ ] Hacer en el celular, en ventana privada, un viaje completo de punta a punta en https://yasale.cuisangelo.com.
- [ ] Anotar cuánto tardaron, en el deploy, un viaje nuevo y `/comparar`. *(Todavía no lo
      medimos; ajustar los tiempos del guion con esas cifras.)*
- [ ] Elegir una ruta de respaldo precargada que ya tenga tramos guardados. Cusco → Aguas
      Calientes es la única que ya probamos de punta a punta.
- [ ] Llevar escritos los tres links: https://yasale.cuisangelo.com, https://yasale.cuisangelo.com/comparar y https://yasale.cuisangelo.com/pitch/.
- [ ] Si el tren Ollantaytambo → Aguas Calientes sale a S/15, es la tarifa del Tren Local, que
      es solo para residentes. PeruRail e Inca Rail publican en dólares, y el esquema en soles
      los descarta. Si aparece, lo digo; nunca lo presento como el precio para un turista.

**En la compu de la organización**, abrir tres pestañas en este orden:

1. `https://yasale.cuisangelo.com/pitch/#2`: slide del problema.
2. `https://yasale.cuisangelo.com/comparar`, con la pregunta ya escrita y sin enviar:
   *"Quiero ir de Lima a la Laguna Azul de Sauce sin tour. ¿Cómo llego y cuánto cuesta cada
   tramo?"*
3. `https://yasale.cuisangelo.com`: inicio.

## Segundo a segundo

| Tiempo | Pantalla | Qué digo y qué hago |
|---|---|---|
| **0:00–0:05** | Pestaña 2 | Envío la pregunta en `/comparar` y paso a la pestaña 1 sin esperar. La comparación hace dos llamadas al modelo, así que se lanza primero y carga mientras hablo. |
| **0:05–0:30** | Pestaña 1, slide 2 | "Para llegar de Lima a la Laguna Azul sin tour hay que armar cuatro tramos: bus o avión a Tarapoto, mototaxi al paradero, auto colectivo a Sauce y balsa. Son cuatro fuentes distintas, y dos de ellas son preguntar en el paradero o leer un blog de hace años. Un chat solo responde de memoria, sin fuente ni fecha. Ya Sale arma el viaje completo con datos que consulta en vivo." |
| **0:30–1:10** | Pestaña 2, `/comparar` | "Es la misma pregunta al mismo modelo, Claude Opus 5.5. A la izquierda va sin herramientas y a la derecha con la herramienta de Ya Sale." Señalo los contadores de abajo: la izquierda dice 0 fuentes y sin fecha; la derecha muestra tramos con fuente y fecha. Leo **un** dato de la izquierda que no tenga fuente y el mismo tramo a la derecha con su página y su hora de consulta. |
| **1:10–1:20** | Pestaña 3, inicio | Le pregunto a un jurado: "¿A qué pueblo va su familia, o a dónde le gustaría ir?". Escribo origen, destino y fecha y aprieto "Armar mi viaje". |
| **1:20–1:55** | Itinerario | Mientras llegan los tramos: "Cada tramo llega por streaming apenas se resuelve. Arriba dice cuántos van de los planeados." Cuando aparece el primero: "Este dice de dónde sale, cuánto cuesta y cuánto demora, y abajo de qué página salió el dato y cuándo se consultó. Si la página no publica el precio, lo dejamos vacío en vez de inventarlo." |
| **1:55–2:15** | Itinerario | "Todos los tramos dicen **Extraído**. Solo una persona puede pasarlos a **Confirmado**." Le paso el mouse a un jurado: "¿Quiere confirmar este tramo, o corregirle el precio?". La tarjeta cambia de estado en pantalla. |
| **2:15–2:30** | `https://yasale.cuisangelo.com/uso` | "La página de uso cuenta viajes, destinos, personas y tramos confirmados desde la base de datos, sin las huellas del equipo. La confirmación de recién ya está acá." Leo las cuatro cifras. |
| **2:30–3:00** | Pestaña 1, slides 4 y 6 | "Por dentro: Tavily y Exa buscan en paralelo, Claude extrae los tramos a un esquema validado, Postgres guarda cada versión con su fuente y su fecha, y todo corre en un contenedor en AWS con la base privada. Las páginas que leemos se tratan como datos no confiables. Un tramo nunca aparece como confirmado sin una persona, y si llega un dato distinto queda en disputa con las dos versiones. El mismo motor está como MCP para usarlo desde ChatGPT o Claude. Gracias." |

Si al llegar a 2:30 voy atrasado, salto la slide 4 y digo solo la frase de la slide 6.

## Plan B si algo tarda

| Si… | Hago |
|---|---|
| `/comparar` no terminó a los 0:30 | Paso a la pestaña 3 y hago primero el destino del jurado (1:10–2:15). Vuelvo a `/comparar` a las 2:15 y dejo `/uso` para las preguntas. |
| `/comparar` dio error | No lo reintento en vivo, porque son dos llamadas largas. Digo "el modelo no respondió a tiempo" y sigo con el itinerario, que muestra lo mismo tramo por tramo. |
| El destino del jurado tarda más de 35 s | Mientras tanto explico los estados (slide 5). Si a los 45 s no llegó ningún tramo, abro la ruta de respaldo, que muestra primero los tramos guardados con su fecha y los refresca en vivo. |
| Responde "No encontramos cómo llegar…" | Es la respuesta correcta y la muestro: "Cuando no hay datos, no inventamos una ruta." Pido un lugar más grande cerca y lo vuelvo a lanzar una sola vez. |
| Un tramo marca error | Es un proveedor que falló en ese tramo. Los demás siguen, y el tramo guardado, si existe, se queda con su fecha. Lo digo y sigo. |
| Aparece "Demasiadas consultas seguidas. Espera un minuto." (429) | Es el límite de 6 consultas por minuto por persona, y lo comparten `/comparar` y los viajes. En la demo hago solo 2 o 3; si salta, hablo de la arquitectura (slide 6) y reintento al minuto. |
| `yasale.cuisangelo.com` no responde pero App Runner sí | Es el DNS o el certificado del dominio. Uso la URL `*.awsapprunner.com` del servicio, que tiene que estar en la descripción entregada justamente para este caso. |
| La URL no responde | No hay video que lo reemplace. A las 09:55 ya probé con `curl`; si falla ahí, aviso a la organización antes de mi turno y pido pasar más tarde. |

## Preguntas probables del jurado

**1. ¿No es ChatGPT con búsqueda web?**
No. Busca y extrae, sí, pero cada tramo se guarda como dato estructurado, con su página, su
fecha y sus versiones. Ese dato lo confirman o corrigen personas, y la siguiente consulta parte
de ahí. Un chat con búsqueda vuelve a empezar cada vez y no distingue lo confirmado de lo
leído.

**2. ¿Qué pasa si el modelo inventa un precio o un paradero?**
La salida del modelo se valida contra un esquema. Se descarta todo tramo cuya fuente no esté
entre las páginas que leímos y todo precio fuera de 0 a 5000 soles. Igual puede leer mal una
página real, y por eso cada tramo muestra su fuente y queda "Extraído" hasta que una persona lo
confirme.

**3. ¿Y si una página trae instrucciones para el modelo?**
Cada página va cercada con un marcador aleatorio, el modelo tiene la instrucción de tratarla
como datos y solo puede devolver JSON validado. No hay herramientas que una página pueda
disparar desde el extractor.

**4. ¿Cómo evitan confirmaciones falsas?**
Una persona puede confirmar una versión una sola vez, y contamos a las personas con una huella
anónima, sin cuentas. La respuesta honesta es que eso no prueba quién es la persona. Por eso
una corrección no borra nada: queda como versión nueva y, si contradice lo confirmado, el tramo
pasa a "en disputa" y se ven las dos versiones.

**5. ¿Qué pasa con un pueblo que no aparece en ninguna web?**
Ya Sale dice que no encontró cómo llegar, en vez de inventar. Para esos lugares el camino es
que alguien que hace la ruta la corrija o la confirme. Por eso la confirmación no necesita
cuenta.

**6. ¿En qué se diferencia de Google Maps, Moovit o redBus?**
Maps y Moovit cubren rutas urbanas con datos de transporte formal. redBus vende el bus
interprovincial. Ninguno conecta el bus con el colectivo, el mototaxi y la lancha en un solo
viaje con su precio. Ya Sale no vende pasajes: enlaza a quien los vende.

**7. ¿Tienen usuarios fuera del equipo?**
Lo que hay está en `/uso`, contado desde la base y sin las huellas del equipo: [viajes,
destinos, personas y confirmaciones al momento de la demo]. Si la cifra es baja, lo digo tal
cual.

**8. ¿Cuánto cuesta y cuánto tarda cada consulta?**
Cada viaje tiene un tope de 8 búsquedas, y la infraestructura en AWS cuesta unos 3 dólares por
día. En la prueba, Tavily tardó 1,2–1,6 s, Exa 3,4–4,1 s y Claude 6,4 s por extracción. El costo
por consulta todavía no lo medimos: [completar si se mide antes de la demo]. Lo guardado
aparece primero, así que una ruta repetida se ve al instante y se refresca después.
