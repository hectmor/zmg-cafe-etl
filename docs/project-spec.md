# Especificación de proyecto: zmg-cafes-etl

## Propósito

Demostrar, de forma educativa y reproducible, cómo observaciones públicas de cafés pasan de OpenStreetMap/Overpass a datos validados, una base PostGIS, una API y un mapa Leaflet.

## Estado y alcance actual

El repositorio completó la extracción raw, la transformación validada, el contrato de base de datos, la carga idempotente y la API FastAPI: incluye configuración de fuente, fixture offline, extractor con snapshots y metadatos, CLI, registros normalizados, advertencias, rechazos, deduplicación determinista, migraciones Flyway para PostgreSQL/PostGIS, carga transaccional con upsert en analytics y endpoints consumer-facing con paginación, detalle, estadísticas y GeoJSON. El frontend aún no está implementado.

## Contrato compartido inicial

Los registros normalizados previstos contienen `source`, `object_type`, `object_id`, `source_id`, `name`, `category`, `latitude`, `longitude`, `geometry`, `geometry_method`, `tags`, `source_updated_at`, `retrieved_at`, `run_id`, `validation_status` y `rejection_reason`. `source_updated_at` es opcional y solo se usa si la fuente lo entrega. `source_id` tiene la serialización canónica `source:object_type:object_id`, por ejemplo `openstreetmap:node:1001`.

Requeridos para un registro aceptado: identidad, categoría, coordenadas válidas, punto en WGS84/SRID 4326, fuente, timestamp de recuperación, ejecución y estado. `name` puede faltar; no se fabrican nombres. `tags` siempre es un objeto y usa `{}` cuando la fuente no entrega tags. GeoJSON usa `[longitude, latitude]`.

`geometry_method` es `node_coordinates` para nodos y `overpass_center` para vías/relaciones. La capa analítica inicial solo representa puntos; el payload raw conserva la respuesta original. `run_id` será un UUID serializado como texto en Python y UUID en la base de datos.

Los estados pertenecen al resultado normalizado/staging: `accepted`, `accepted_with_warning` o `rejected`. Un rechazado conserva `rejection_reason` y no entra a analytics. Un registro fuera del área se conserva para auditoría con razón `outside_study_area`, distinto de una coordenada inválida. `accepted_with_warning` permite análisis cuando las invariantes estructurales se cumplen, por ejemplo nombre ausente o punto derivado de `center`.

## Fases de trabajo

1. Fuente y extracción raw.
2. Validación y transformación.
3. PostgreSQL/PostGIS y migraciones Flyway.
4. Carga idempotente.
5. FastAPI.
6. Frontend Leaflet.
7. Compose, pruebas de integración y CI.
8. Observabilidad y hardening.

No se comienza una fase dependiente hasta que su contrato de entrada y aceptación hayan sido revisados.
