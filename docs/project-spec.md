# Especificación de proyecto: zmg-cafes-etl

## Propósito

Demostrar, de forma educativa y reproducible, cómo observaciones públicas de cafés pasan de OpenStreetMap/Overpass a datos validados, una base PostGIS, una API y un mapa Leaflet.

## Estado y alcance actual

El repositorio completó la extracción raw, la transformación validada, el contrato de base de datos, la carga idempotente, la API FastAPI, el frontend Leaflet, Compose/CI (M7) y el primer tramo de hardening (M8.1): incluye configuración de fuente, fixture offline, extractor con snapshots y metadatos, CLI, registros normalizados, advertencias, rechazos, deduplicación determinista, migraciones Flyway para PostgreSQL/PostGIS, carga transaccional con upsert en analytics, endpoints consumer-facing con paginación, detalle, estadísticas, GeoJSON, estado y frescura de ejecuciones (`GET /runs`), y un mapa con búsqueda, filtros, marcadores y atribución.

El milestone M9 (issue #58) agregó INEGI DENUE como segunda fuente configurable, sin reemplazar OpenStreetMap/Overpass. `SourceConfig` ahora modela dos `access_method`: `overpass_api` (bbox + Overpass QL) y `inegi_denue_api` (paginado por municipio de la ZMG vía el endpoint `BuscarAreaAct`, filtrado por SCIAN `722515`). El extractor DENUE (`extract_denue.py`) pide ventanas de registros por municipio y se detiene cuando una ventana devuelve menos registros que el tamaño pedido; cada registro crudo se mapea a la misma forma de elemento genérico (`type`, `id`, `tags`) que ya usan los elementos de Overpass, conservando todos sus campos originales, para reutilizar sin cambios el snapshot, la transformación y la deduplicación existentes. El token de DENUE se lee de la variable de entorno `INEGI_DENUE_TOKEN`; nunca se guarda en `config/sources.yaml` ni se imprime en logs o metadata.

## Contrato compartido inicial

Los registros normalizados previstos contienen `source`, `object_type`, `object_id`, `source_id`, `name`, `category`, `establishment_kind`, `municipio`, `ubicacion`, `areageo`, `clee`, `latitude`, `longitude`, `geometry`, `geometry_method`, `tags`, `source_updated_at`, `retrieved_at`, `run_id`, `validation_status` y `rejection_reason`. `source_updated_at` es opcional y solo se usa si la fuente lo entrega. `source_id` tiene la serialización canónica `source:object_type:object_id`, por ejemplo `openstreetmap:node:1001`.

`establishment_kind` (`cafe`, `neveria`, `refresqueria` u `otro`) es una clasificación heurística derivada del nombre comercial (`classify.py`), **no un dato oficial de INEGI ni de OSM**: existe porque el SCIAN `722515` agrupa cafeterías, neverías, fuentes de sodas y refresquerías en una sola clase sin distinguirlas. Para OpenStreetMap siempre es `cafe` (hecho de la fuente, la consulta ya filtra `amenity=cafe`); para INEGI DENUE se infiere por palabras clave en `Nombre`/`Razon_social`, con prioridad `neveria` > `refresqueria` > `cafe` > `otro`, y nunca se fabrica `cafe` por defecto ante ausencia de señal.

`municipio` es, a diferencia de `establishment_kind`, un dato **oficial, no heurístico**: INEGI DENUE se consulta por `BuscarAreaAct` con un `entidad`+`municipio` conocido de `config/sources.yaml` por cada uno de los 9 municipios de la ZMG, así que cada registro se etiqueta con el nombre exacto del municipio de la consulta que lo devolvió (`extract_denue.py`); nunca se infiere ni se parsea el texto libre `Ubicacion`/`AreaGeo` de la respuesta de INEGI. Para OpenStreetMap siempre es `None`/NULL, porque Overpass no provee este atributo.

`ubicacion`, `areageo` y `clee` son también campos **oficiales y crudos de INEGI DENUE** (`Ubicacion`, `AreaGeo`, `CLEE` del registro), no heurísticos: ya vienen completos en cada registro DENUE y `transform.py` solo los copia tal cual, sin parsear ni derivar nada de ellos. Para OpenStreetMap siempre son `None`/NULL, porque Overpass no los provee.

Requeridos para un registro aceptado: identidad, categoría, coordenadas válidas, punto en WGS84/SRID 4326, fuente, timestamp de recuperación, ejecución y estado. `name` puede faltar; no se fabrican nombres. `tags` siempre es un objeto y usa `{}` cuando la fuente no entrega tags. GeoJSON usa `[longitude, latitude]`.

`geometry_method` es `node_coordinates` para nodos y `overpass_center` para vías/relaciones de OpenStreetMap, y `denue_coordinates` para unidades económicas de INEGI DENUE (lat/lon directos del registro, campos `Latitud`/`Longitud`). `object_type` de DENUE es siempre `economic_unit` y `object_id` es el `Id` entero del registro DENUE; `source_id` para esta fuente sigue el mismo patrón `source:object_type:object_id`, por ejemplo `inegi_denue:economic_unit:7026403001`. La capa analítica inicial solo representa puntos; el payload raw conserva la respuesta original. `run_id` será un UUID serializado como texto en Python y UUID en la base de datos.

Los estados pertenecen al resultado normalizado/staging: `accepted`, `accepted_with_warning` o `rejected`. Un rechazado conserva `rejection_reason` y no entra a analytics. Un registro fuera del área se conserva para auditoría con razón `outside_study_area`, distinto de una coordenada inválida. `accepted_with_warning` permite análisis cuando las invariantes estructurales se cumplen, por ejemplo nombre ausente o punto derivado de `center`.

Un registro aceptado en una corrida anterior que en la corrida actual está ausente o rechazado se retira de `analytics.establecimientos` (ADR-006); `staging.cafe_records` y `raw.overpass_snapshots` conservan su historial completo.

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
