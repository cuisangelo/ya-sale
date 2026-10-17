# Idea

Un viaje, de la casa en Lima al pueblo, con cada tramo y su precio. El ejemplo que define el producto es ir a Sauce, a la Laguna Azul, sin tour.

## Quién y qué hace

La persona abre la página, dice a dónde va y en qué fechas. Sale de Lima. La página le arma el viaje en el orden en que se hace:

1. Lima → Tarapoto, en bus o en avión.
2. En Tarapoto, el tramo local hasta el paradero de los autos a Sauce.
3. El auto compartido que sale cuando llena y la deja en Sauce, con el tiempo estimado.

La acción que tiene que poder completar es ver ese viaje completo y decidir, antes de salir, qué tramo comprar y cuál todavía no está confirmado.

## Cómo se resuelve hoy

En la ciudad usa Google Maps o TuRuta. El bus a Tarapoto lo busca en redBus o en la página de la empresa. El vuelo, en la aerolínea. El auto a Sauce se entera en Tarapoto, en el paradero, o le pregunta a alguien. Nadie junta los tres tramos ni el precio total.

## Qué muestra la página

- **Bus.** No copiamos el inventario de redBus. Enlazamos la búsqueda Lima–Tarapoto para que vea salidas y compre allá. Las guías públicas hablan de un viaje de unas 24 a 28 horas, con varias empresas saliendo por la tarde, a menudo desde Plaza Norte. Eso es contexto, no una tarifa nuestra.
- **Avión.** El horario y el precio se consultan donde se compra el pasaje. La página redirige. No guarda una tarifa propia ni compara aerolíneas.
- **Tarapoto → Sauce.** Este tramo solo se afirma si alguien que lo hace lo confirmó: de qué paradero sale, cuánto cobra y cuánto demora. Si nadie lo confirmó, la página dice que no lo tiene.

Las guías publicadas describen un colectivo que sale cuando llena, desde la Banda de Shilcayo o desde el cruce hacia Yurimaguas, cobra entre S/10 y S/15 y tarda cerca de 1 h 45 min a 2 h. El camino cruza el río Huallaga en la balsa de Puerto López. La moto que lleva hasta ese paradero, y la moto de alquiler para hacer la carretera uno mismo, son otra cosa: la primera no está publicada como un servicio con cupos, y la segunda es un alquiler por día, no un pasaje. Hasta que alguien de Sauce o de Tarapoto lo confirme, la página no dice "hay motos disponibles".

## Aviso de las empresas

Una empresa o un cobrador puede publicar "nos faltan tantos cupos" para una salida. Ese aviso solo aparece si ellos lo escribieron. La demo no inventa cupos. Sin un aviso real, ese espacio queda vacío.

## Evidencia

El hueco está medido en el producto de los demás: Maps y TuRuta se quedan en la ciudad, redBus vende el bus y no engancha el auto de Sauce. No hay evidencia todavía de que esta página le evite un trasbordo mal hecho. Esa evidencia es una persona que haga la ruta y diga si el paradero y el precio son los que usa.

## Qué queda fuera

El mapa del Perú, la tarjeta única, hoteles, tours, el GPS de los buses, la cola del Metropolitano y una cuenta de usuario. Mañana se demuestra un solo viaje: Lima, unas fechas, Sauce. Los tramos con enlace van a quien vende el pasaje. El tramo local va con el nombre de quien lo confirmó, o con la frase de que todavía no está confirmado.

## Fuentes de la ruta

- [redBus, Lima a Tarapoto](https://www.redbus.pe/pasajes-de-bus/lima-a-tarapoto)
- [Buscobus, Lima a Tarapoto](https://buscobus.pe/horarios-y-pasajes/lima-a-tarapoto-en-bus/)
- [Laguna Azul, cómo llegar en colectivo](https://tarapoto.net/lugares-turisticos/laguna-azul-sauce/)
- [Apu Samay, colectivo, balsa y moto](https://apusamay.com/como-llegar-a-la-laguna-azul-desde-tarapoto/)
