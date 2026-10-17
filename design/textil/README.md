# Identidad textil andina

Estilo de Ya Sale: **rombo de hebras, hecho a mano, con toques de hilo**. Son motivos del tejido
andino en vector, sin pixel art:

- rellenos con hebras de grosor y tono variables;
- con un leve temblor en los bordes y textura de fibra, para que no se vean "demasiado
  perfectos";
- unidos por líneas finas que conectan los tramos como un hilo.

El acabado artesanal es el filtro SVG `feTurbulence` + `feDisplacementMap` que traen `logo-inti.svg`
y `franja.svg`. Los motivos son diseños propios inspirados en el pallay y no copian el de
ninguna comunidad. Los significados del pallay cambian de comunidad en comunidad, y abajo está la
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
| `logo-inti.svg` | Inti: franjas en rombo (cochinilla, q'olle y añil) con hebras en diagonal, hecho a mano | Logo y destino |
| `motivo-chakana.svg` | Chakana, cruz escalonada | Transbordo entre transportes |
| `motivo-chaska.svg` | Ch'aska, estrella | Tramo confirmado por alguien que lo hace |
| `motivo-mayu.svg` | Mayu, zigzag del río | El hilo que une los tramos, girado en vertical |
| `franja.svg` | Franja de hebras con dientes en zigzag y rombos, hecha a mano | Borde superior e inferior, como el de una manta |

### Por qué son peruanos

- **En los tejidos Q'ero del Cusco, el inti (sol) se teje como franjas en forma de rombo.**
  Fuente: Bard Graduate Center, análisis de una bolsa de coca Q'ero.
- **El rombo es un motivo peruano continuo desde Nazca, Wari, Tiahuanaco e Inca hasta hoy.**
  Fuente: Gail Silverman-Proust, *Anthropologica* (PUCP), y *Tejido Q'ero, una ventana a la
  sabiduría inca* (Cultura Cusco, 2020).
- **Los colores son los de los tintes naturales andinos:** cochinilla, q'olle y añil.
- **Para no confundirlo con el "ojo de Dios" mexicano:** tejido de hebras, paleta de tintes
  andinos y centro añil.

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
