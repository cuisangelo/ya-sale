# Identidad textil andina

Estilo de Ya Sale: **rombo de hebras con toques de hilo**. Motivos del tejido andino dibujados
en vector limpio (sin pixel art), rellenos con hebras verticales de urdimbre, y líneas finas que
unen los tramos como un hilo. Los motivos son diseños propios inspirados en el pallay; no copian el de ninguna
comunidad. Los significados del pallay cambian de comunidad en comunidad, y abajo está la
lectura que les damos dentro del producto.

## Paleta (tintes naturales)

| Color | Hex | Origen | Uso |
|---|---|---|---|
| Cochinilla | `#B5172F` | Insecto del nopal | Marca, botón principal, tramos por tierra |
| Cochinilla púrpura | `#6E1F4F` | Cochinilla con otro mordiente | Acentos |
| Q'olle | `#E8B419` | Flor del arbusto qolle | Tramos aéreos, estado "en disputa" |
| Q'olle oscuro | `#8A6700` | — | Ícono de avión sobre fondo claro |
| Ch'illka | `#4F6B2A` | Hojas de chilca | Tramos en riel, estado "confirmado" |
| Añil | `#23356F` | Índigo | Tramos por agua, transbordo, enlaces |
| Lana natural | `#F4EBDA` | — | Fondo |
| Lana oscura | `#2A1F1A` | — | Texto |
| Hilo | `#CDBFA6` | — | Zigzag que une los tramos, divisores |
| Texto secundario | `#6B5E52` | — | Fuentes y fechas |

## Motivos

| Archivo | Motivo | En Ya Sale |
|---|---|---|
| `logo-tawa-inti.svg` | Tawa inti qocha: rombo con el centro dividido en cuatro, relleno de hebras verticales | Logo y destino |
| `motivo-chakana.svg` | Chakana, cruz escalonada | Transbordo entre transportes |
| `motivo-chaska.svg` | Ch'aska, estrella | Tramo confirmado por alguien que lo hace |
| `motivo-mayu.svg` | Mayu, zigzag del río | El hilo que une los tramos, girado en vertical |
| `franja.svg` | Franja de urdimbre con triángulos qocha y un rombo en cuatro | Borde superior e inferior, como el de una manta |

### Por qué son peruanos

- **El rombo en cuatro (*tawa inti qocha*, "cuatro-sol-lago") existe en el Perú desde Nazca,
  Wari, Tiahuanaco e Inca hasta hoy.** Es central en los tejidos Q'ero del Cusco, donde "inti"
  (sol) es un rombo. Fuente: Gail Silverman-Proust, *Anthropologica* (PUCP), y *Tejido Q'ero,
  una ventana a la sabiduría inca* (Cultura Cusco, 2020).
- **El tejido andino de telar de cintura es de cara de urdimbre.** El color visible es el de
  los hilos verticales, por eso la textura de hebras es vertical.
- **Los triángulos alternos junto al inti se llaman *qocha* (lago)** en los tejidos Q'ero.
- **Lo que evitamos:** los anillos concéntricos sin división, para no confundirlo con el
  "ojo de Dios" mexicano.

## Íconos de transporte

`modo-<medio>.svg` para bus, combi, colectivo, mototaxi, avión, tren y lancha. Son de trazo
(24 × 24, 1,8 px, puntas redondeadas) y se colorean cambiando `stroke`. El color va por medio:

- tierra en cochinilla;
- aire en q'olle oscuro;
- riel en ch'illka;
- agua en añil.

En la tarjeta del tramo, el ícono va dentro de un círculo de contorno del mismo color.

## Tarjeta de tramo

- Fondo blanco, esquinas de 6 px y barra izquierda de 6 px del color del medio.
- Fuente y fecha en JetBrains Mono, en texto secundario.
- **Estados, distintos por forma y texto, no solo por color:**
  - Extraído: contorno gris.
  - En disputa: q'olle sólido.
  - Confirmado: ch'illka sólido con la estrella ch'aska.
- Entre tramos, el zigzag mayu en color hilo. Si hay cambio de transporte, va la chakana con
  "Transbordo en …".

## Tipografía

- **Bricolage Grotesque 800:** títulos y logo.
- **Archivo:** texto e interfaz.
- **JetBrains Mono:** fuentes, fechas y precios.

## Respeto por el origen

Si el proyecto sigue después del hackathon, la identidad se trabaja con una cooperativa de
tejedoras y se les da crédito.
