# Tutorial 02: contrato de extracción

La primera parte de esta etapa ya está implementada con un modo offline determinista. La consulta live está disponible, pero no forma parte de las pruebas automáticas.

## Contrato

La entrada puede ser una respuesta Overpass live o un fixture offline. La salida conserva el JSON original en `data/raw`, registra fuente, consulta/hash, timestamps y ejecución, y falla explícitamente ante errores HTTP, JSON mal formado o una estructura sin `elements`.

Ejecuta el modo offline con:

```bash
python -m zmg_cafes_etl --offline tests/fixtures/overpass_cafes_sample.json
```

El comando imprime un resumen JSON con `run_id`, cantidad de objetos y rutas del snapshot y sus metadatos. Para evitar sobrescrituras, cada ejecución genera un nuevo UUID.

## Criterios de aceptación

- timeout de conexión y lectura configurados;
- reintentos acotados con backoff;
- snapshot particionado por fecha y `run_id`;
- modo offline determinista;
- ningún snapshot previo sobrescrito;
- pruebas sin depender de Internet.

## Ejercicio

Diseña una prueba para demostrar que una segunda ejecución no reemplaza el snapshot de la primera. La transformación será la siguiente etapa y recibirá este resultado estructurado.
