# Handoff para continuar el proyecto

Este documento describe el estado del checkout y la tarea concreta para el siguiente modelo.

## Estado al 13 de octubre de 2026

- M1 extracción: implementada. `extract_offline` y `extract_live` escriben snapshot JSON y metadatos; la petición live está cubierta mediante HTTP simulado, no contra Overpass.
- M2 transformación: implementada como biblioteca. `transform_payload` normaliza `node`, `way` y `relation`, crea GeoJSON `[longitude, latitude]`, asigna advertencias/rechazos y conserva el primer objeto de cada identidad duplicada.
- M3 base de datos: implementada y aplicada con Flyway 13.6.0 sobre PostgreSQL 17.5/PostGIS. La versión 1 crea schemas/tablas, constraints y los dos índices GiST.
- M4 carga/pipeline: implementada. `load_run` persiste cada ejecución en una transacción (`meta.pipeline_runs`, `raw.overpass_snapshots`, staging completo y solo aceptados en analytics) con upsert idempotente por `source_id`. La migración `V2__partial_unique_accepted_identity.sql` permite auditar duplicados rechazados sin romper la unicidad de aceptados. El CLI acepta `--database-url` y reporta métricas.
- M5 API FastAPI: implementada. El paquete `api/` (separado del ETL) expone solo la capa `analytics` con `GET /health`, `GET /cafes` (paginado), `GET /cafes/{source_id}`, `GET /geojson/cafes` y `GET /stats`. Se sirve con `python -m uvicorn api.main:app` usando `DATABASE_URL`.
- M6 frontend Leaflet: implementado. `frontend/` es un cliente estático sin frameworks: mapa de la ZMG, búsqueda por nombre, filtro por `object_type`, marcadores con popup, estados de carga/error y atribución de OpenStreetMap/Overpass/Leaflet. Consume solo la API; se sirve con `python -m http.server 8080 --directory frontend` y la API habilita CORS para ese origen.

Los milestones están commiteados por fase en ramas con PR a `develop`.

## Entorno y comandos verificados

El entorno Conda `zmg-cafe` disponible en esta máquina usa Python 3.14.8, fuera del rango declarado en `pyproject.toml` (`>=3.12,<3.14`). Ruff, pytest y psycopg están instalados allí. Como el paquete no está instalado editable, las pruebas se ejecutaron así:

```bash
conda run -n zmg-cafe python -m ruff check .
conda run -n zmg-cafe python -m ruff format --check .
conda run -n zmg-cafe env PYTHONPATH=src python -m pytest
```

Resultado al cerrar M6: Ruff OK, formato OK, 67 pruebas aprobadas (54 sin BD y 13 de integración contra PostGIS), `git diff --check` OK y Flyway 13.6.0 con las versiones 1 y 2 aplicadas. Instalar/ejecutar con Python 3.12 o 3.13 sigue pendiente. El renderizado del frontend en navegador no se verificó con automatización; solo se probó por HTTP.

Las pruebas de integración en `tests/integration/` limpian los cuatro schemas antes de cada prueba; requieren una base de desarrollo accesible vía `ZMG_TEST_DATABASE_URL` y se omiten si la variable no está definida:

```bash
conda run -n zmg-cafe env PYTHONPATH=src \
  ZMG_TEST_DATABASE_URL=postgresql://zmg_cafes:zmg_cafes_dev@localhost:PUERTO/zmg_cafes \
  python -m pytest
```

La base local se levanta con `POSTGRES_PORT=0 docker compose up -d db`; Docker asigna un puerto aleatorio del host (consulta el actual con `docker port zmg-cafe-etl-db-1`). Las migraciones se aplican con `POSTGRES_PORT=0 docker compose --profile migrate run --rm flyway`. El volumen Docker `postgres_data` conserva el esquema migrado. Para detenerlo sin borrar los datos: `docker compose stop db`. No ejecutar `down -v`. Nunca ejecutes `docker compose run` sin `POSTGRES_PORT=0` mientras otro servicio use el puerto 5432: recrea el contenedor con el puerto por defecto y falla.

## Contrato de persistencia existente

Las migraciones están en `db/migrations` y Flyway es el único migrador permitido.

- `meta.pipeline_runs`: una ejecución, UUID, fuente, timestamps y estado.
- `raw.overpass_snapshots`: consulta/hash, payload JSONB y ruta del snapshot.
- `staging.cafe_records`: filas aceptadas y rechazadas, estado y razón; `geometry` es `Point, 4326` y es nula en rechazos.
- `analytics.cafes`: estado consultable actual por `source_id`, con clave primaria y geometría `Point, 4326`.
- `run_id` corresponde a `ExtractionResult.run_id`; `retrieved_at`, query, hash, payload y ruta provienen de `ExtractionResult`.
- La geometría se construye en SQL como `ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)`; GeoJSON y PostGIS usan longitud antes que latitud.
- Desde V2, la unicidad de `(run_id, source_id)` en staging solo aplica a `accepted`/`accepted_with_warning` (índice `staging_run_accepted_identity`); los duplicados rechazados se conservan como filas propias.

## Tarea y aceptación para M7

1. Completar `compose.yaml` para levantar el pipeline completo de forma reproducible (base, migraciones, API y frontend según aplique).
2. Automatizar pruebas de integración y migraciones Flyway en CI.
3. Validar la instalación limpia desde un checkout nuevo siguiendo la documentación.
4. Documentar los comandos operativos y actualizar `README.md` y `docs/milestones.md`.
5. No expandir M7 a observabilidad ni hardening (M8).

No agregar Alembic. Usa SQL versionado por Flyway para cambios de esquema y respeta el contrato de `docs/data_dictionary.md`.
