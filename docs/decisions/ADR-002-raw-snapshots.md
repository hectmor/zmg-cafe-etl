# ADR-002: Preservar snapshots raw inmutables

- **Estado:** aceptado
- **Contexto:** una transformación reproducible requiere poder inspeccionar exactamente la respuesta recibida.
- **Opciones:** guardar solo registros transformados, guardar la respuesta completa, depender de repetir la consulta.
- **Decisión:** guardar cada respuesta completa en una ruta particionada por fuente/fecha/run y acompañarla con metadatos.
- **Consecuencias:** aumenta almacenamiento local, pero permite auditoría, pruebas offline y comparación entre ejecuciones; snapshots productivos no se versionan en Git.
