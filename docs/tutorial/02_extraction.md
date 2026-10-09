# Tutorial 02: contrato de extracción

Esta etapa está especificada, pero el código se implementará en el siguiente milestone.

## Contrato

La entrada puede ser una respuesta Overpass live o un fixture offline. La salida deberá conservar el JSON original, registrar fuente, consulta/hash, timestamps y ejecución, y fallar explícitamente ante HTTP errors, JSON mal formado o una estructura sin `elements`.

## Criterios de aceptación

- timeout de conexión y lectura configurados;
- reintentos acotados con backoff;
- snapshot particionado por fecha y `run_id`;
- modo offline determinista;
- ningún snapshot previo sobrescrito;
- pruebas sin depender de Internet.

## Ejercicio

Diseña una prueba para demostrar que una segunda ejecución no reemplaza el snapshot de la primera. La transformación será la siguiente etapa y recibirá este resultado estructurado.
