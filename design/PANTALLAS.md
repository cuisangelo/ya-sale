# Pantallas del MVP

Aprobadas por Cuiso el 2026-10-17. El mockup de referencia es `design/pantallas-mockup.html`,
un fragmento con estilos en línea; las clases `option` y `mockup-header` son del visor y no se
copian. Los recursos y la anatomía de la tarjeta de tramo están en
[`textil/README.md`](textil/README.md). Todo texto entre corchetes es un dato real que todavía
no tenemos; nunca se inventa.

## Reglas comunes

- Fondo lana natural `#F4EBDA` y franja tejida (`textil/franja.svg`) arriba de la página.
- Logo `textil/logo-inti.svg` junto a "Ya Sale" en Bricolage Grotesque 800, color cochinilla.
- Inputs: fondo `#FBF7F0`, borde 1,5 px `#CDBFA6`, esquinas de 6 px, texto lana oscura. Nunca
  fondo oscuro.
- Botón principal sólido cochinilla con texto lana; el secundario en contorno lana oscura.
- Las páginas son fluidas: en un celular las grillas pasan a una columna.

## 1 · Inicio

1. Logo y título "¿De dónde a dónde vas?".
2. Subtítulo con los modos de transporte.
3. Formulario: origen, destino y fecha de salida (solo ida), con el botón "Armar mi viaje".
4. Chips de ejemplo de todo el país: Cusco → Aguas Calientes, Iquitos → Nauta, Lima → Sauce y
   Arequipa → Chivay.
5. Pie con la URL del MCP para ChatGPT o Claude y links a la comparación y al uso en vivo.

## 2 · Itinerario

1. **Encabezado:** origen → destino, más "N tramos · tiempo total · precio total".
2. **Indicador en vivo:** "Actualizando en vivo · k de N tramos".
3. **Tarjetas de tramo en orden,** unidas por el zigzag mayu. Hay un rótulo "Transbordo en …"
   cuando cambia el medio.
4. **Cada tramo muestra:**
   - el modo, con su ícono y su color;
   - de dónde sale;
   - precio, tiempo y link de compra si existe;
   - la fuente y la frescura: "actualizado hace N s", o "guardado [fecha] · refrescando…"
     mientras llega el dato en vivo;
   - el estado: Extraído, En disputa o Confirmado.
5. **Acciones:** "¿Hiciste esta ruta? Confírmala", "Corregir un tramo" y "Compartir".

## 3 · Comparación (la pantalla de la demo)

1. La pregunta en lenguaje natural arriba.
2. **Dos columnas con el mismo modelo:**
   - "Claude solo", con la respuesta real del modelo sin herramientas y el contador
     "0 fuentes · sin fecha";
   - "Claude + Ya Sale", con los tramos, sus fuentes y sus estados.
3. **Contadores abajo:** tramos con fuente, datos con fecha y confirmados por personas.

## 4 · Uso en vivo

1. **Cuatro cifras de la base real:**
   - viajes armados;
   - destinos distintos;
   - personas distintas, contadas con una huella anónima y sin datos personales;
   - tramos confirmados.
2. Lista de las últimas confirmaciones y correcciones, con la hora relativa.
3. Nota: sin cuentas del equipo ni tráfico automatizado. Es lo que exige el bonus de tracción.
