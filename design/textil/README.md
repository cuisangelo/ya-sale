# Identidad textil andina

Recursos visuales de Ya Sale: motivos e íconos dibujados pixel a pixel sobre la grilla del
tejido, inspirados en el pallay andino. Son diseños propios y no copian el pallay de ninguna
comunidad. Los significados del pallay cambian de comunidad en comunidad; abajo está la
lectura que les damos dentro del producto.

Para regenerar los SVG: `uv run --no-project python design/textil/generate.py design/textil`.

## Paleta (tintes naturales)

| Color | Hex | Origen | Uso |
|---|---|---|---|
| Cochinilla | `#B5172F` | Insecto del nopal | Marca, tramos por tierra |
| Cochinilla púrpura | `#6E1F4F` | Cochinilla con otro mordiente | Acentos |
| Q'olle | `#E8B419` | Flor del arbusto qolle | Tramos aéreos, estado "en disputa" |
| Ch'illka | `#4F6B2A` | Hojas de chilca | Tramos en riel, estado "confirmado" |
| Añil | `#23356F` | Índigo | Tramos por agua, enlaces |
| Lana natural | `#F4EBDA` | — | Fondo |
| Lana oscura | `#2A1F1A` | — | Texto |

Sobre fondo de lana natural, el ícono de avión usa `#B98A00` (q'olle oscurecido) para
contrastar.

## Motivos

| Archivo | Motivo | En Ya Sale |
|---|---|---|
| `motivo-inti.svg` | Inti, rombo concéntrico | El destino; también el logo |
| `motivo-chakana.svg` | Chakana, cruz escalonada | Transbordo entre transportes |
| `motivo-chaska.svg` | Ch'aska, estrella | Tramo confirmado por alguien que lo hace |
| `motivo-mayu.svg` | Mayu, zigzag del río | La línea que une los tramos |
| `franja.svg` | Franja tejida | Bordes y separadores, repetida en horizontal |

## Íconos de transporte

`modo-<medio>.svg` para bus, combi, colectivo, mototaxi, avión, tren y lancha. Cada uno trae
el color de su medio (tierra, aire, riel o agua) y se puede cambiar el `fill`. Se dibujan con
`shape-rendering="crispEdges"` para que el pixel tejido se vea nítido a cualquier tamaño.

## Tipografía

- **Bricolage Grotesque 800:** títulos y logo.
- **Archivo:** texto e interfaz.
- **JetBrains Mono:** fuentes, fechas y precios.

## Respeto por el origen

Si el proyecto sigue después del hackathon, la identidad se trabaja con una cooperativa de
tejedoras y se les da crédito.
