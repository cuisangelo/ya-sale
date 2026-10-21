# Preferencias de viaje

En cada viaje se puede recordar «de día», «de noche» o «precio más bajo», con consentimiento explícito. En el siguiente viaje, «Consejos para ti» destaca salidas publicadas que encajan. Se pueden cambiar o borrar. Los consejos respetan los asientos disponibles y muestran sus enlaces originales; no inventan precios ni modifican la búsqueda de transporte.

## Activación opcional

Configurar las cuatro variables del backend juntas. Sin ellas, Ya Sale conserva su flujo actual sin consultar memoria.

- `ATOMICMEMORY_API_URL`: URL base de Atomic Memory Core o Cloud compatible con su API Core. HTTPS, salvo loopback para desarrollo.
- `ATOMICMEMORY_API_KEY`: credencial del servidor. Nunca se entrega al navegador.
- `TRAVELER_COOKIE_SECRET`: secreto aleatorio de al menos 32 caracteres para firmar la identidad anónima.
- `PUBLIC_ORIGIN`: origen público de Ya Sale, incluyendo protocolo y puerto si corresponde, sin ruta.

Una cookie Secure, HttpOnly y SameSite=Lax dura 180 días. Cada navegador recibe un identificador aleatorio firmado por el servidor. Atomic Memory recibe solo esa identidad y las dos preferencias estructuradas, sin nombre, IP, destino ni historial de viajes. Se usa únicamente `user_id`, sin `thread` compartido, y `source_site=ya-sale`. `metadata.externalId` mantiene una preferencia actual por persona. Borrar elimina los registros de esta integración y después la cookie. Si falla el guardado o el borrado, la identidad consentida se conserva para reintentar o borrar un guardado cuya confirmación se perdió. La caducidad de la cookie no borra automáticamente los datos del proveedor: usar el botón de borrado o la política de retención de la instancia.

Las operaciones tienen un límite de tres segundos. Las respuestas vacías o malformadas no se presentan como guardado o borrado confirmado. Una caída del proveedor no impide ver las salidas.

## Demo reproducible

La captura y el video muestran la aplicación real con PostgreSQL desechable, salidas sintéticas de `example.com` y un proveedor HTTP local de prueba. No son una reserva ni una conexión a Atomic Memory de producción.

1. Instalar el frontend con `pnpm install --frozen-lockfile` y generar `pnpm build` desde `web`.
2. Instalar dependencias de desarrollo con `uv sync --frozen --group dev` desde `backend`.
3. Con `DATABASE_URL` apuntando a una base PostgreSQL **desechable**, ejecutar desde `backend`: `PYTHONPATH=.:tests uv run python scripts/demo_traveler_memory.py`.
4. Abrir `http://localhost:4830/viaje/?o=Lima&d=Trujillo&f=2026-10-25`. Guardar noche y precio más bajo, recargar, cambiar a día y borrar. Los puertos 4830 y 4831 escuchan únicamente en loopback.

Los tests de backend usan otra base desechable y truncan sus tablas. Nunca ejecutar con una base de producción.
