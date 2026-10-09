# Flujo de datos

## Flujo planeado

1. Construir una consulta Overpass desde `config/sources.yaml`.
2. Obtener un JSON con elementos `node`, `way` y `relation` cuando aplique.
3. Guardar el payload original junto con `run_id`, consulta/hash, timestamps y fuente.
4. Convertir cada elemento a un registro normalizado.
5. Separar registros válidos y rechazados con razones explícitas.
6. Cargar staging y después analytics dentro de límites transaccionales documentados.
7. Servir solo la capa consumer-facing a la API.

## Identidad y tiempo

`source + object_type + object_id` identifica una observación de fuente. `retrieved_at` indica cuándo se obtuvo; no se interpreta como fecha de modificación de OpenStreetMap. Una ausencia posterior no será una baja confirmada.

## Secuencia futura

```mermaid
sequenceDiagram
  participant C as CLI
  participant E as Extractor
  participant O as Overpass
  participant R as Raw store
  participant T as Transformer
  participant D as Database
  C->>E: start(run_id, config)
  E->>O: POST query with timeout
  O-->>E: JSON response
  E->>R: persist immutable snapshot
  E->>T: extraction result
  T-->>C: valid + rejected + metrics
  C->>D: stage and upsert in transaction
  D-->>C: load metrics and status
```
