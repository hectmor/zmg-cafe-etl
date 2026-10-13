# Handoff para continuar el proyecto

Este documento describe el estado del checkout y la tarea concreta para el siguiente modelo.

## Estado al 12 de octubre de 2026

- M1 extracción: implementada. `extract_offline` y `extract_live` escriben snapshot JSON y metadatos; la petición live está cubierta mediante HTTP simulado, no contra Overpass.
- M2 transformación: implementada como biblioteca. `transform_payload` normaliza `node`, `way` y `relation`, crea GeoJSON `[longitude, latitude]`, asigna advertencias/rechazos y conserva el primer objeto de cada identidad duplicada.
- M3 base de datos: implementada y aplicada con Flyway 13.6.0 sobre PostgreSQL 17.5/PostGIS. La versión 1 crea schemas/tablas, constraints y los dos índices GiST.
- M4 carga/pipeline: pendiente. No existe conexión Python a PostgreSQL, loader ni comando ETL que escriba en las tablas.
- API y frontend: pendientes.
- El árbol de trabajo contiene cambios sin commit de M1, M2 y M3. Revísalos antes de trabajar; no descartes ni sobrescribas cambios ajenos.

## Entorno y comandos verificados

El entorno Conda `zmg-cafe` disponible en esta máquina usa Python 3.14.8, fuera del rango declarado en `pyproject.toml` (`>=3.12,<3.14`). Ruff y pytest están instalados allí. Como el paquete no está instalado editable, las pruebas se ejecutaron así:

```bash
conda run -n zmg-cafe python -m ruff check .
conda run -n zmg-cafe python -m ruff format --check .
conda run -n zmg-cafe env PYTHONPATH=src python -m pytest
```

Resultado al cerrar M3: Ruff OK, formato OK, 33 pruebas aprobadas, `git diff --check` OK y `docker compose --profile migrate config --quiet` OK. Instalar/ejecutar con Python 3.12 o 3.13 sigue pendiente.

La migración fue comprobada en un contenedor local. Los puertos 5432 y 5433 estaban ocupados y se usó `POSTGRES_PORT=0`; Docker lo publicó actualmente en el puerto 32768 del host. El contenedor seguía activo al revisar el handoff. El volumen Docker `postgres_data` conserva el esquema migrado. Para detenerlo sin borrar los datos: `POSTGRES_PORT=0 docker compose stop db`. No ejecutar `down -v`.

## Contrato de persistencia existente

La migración está en `db/migrations/V1__initial_geospatial_schema.sql` y Flyway es el único migrador permitido.

- `meta.pipeline_runs`: una ejecución, UUID, fuente, timestamps y estado.
- `raw.overpass_snapshots`: consulta/hash, payload JSONB y ruta del snapshot.
- `staging.cafe_records`: filas aceptadas y rechazadas, estado y razón; `geometry` es `Point, 4326`.
- `analytics.cafes`: estado consultable actual por `source_id`, con clave primaria y geometría `Point, 4326`.
- `run_id` debe corresponder a `ExtractionResult.run_id`; `retrieved_at`, query, hash, payload y ruta provienen de `ExtractionResult`.
- La geometría se construye en SQL como `ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)`; GeoJSON y PostGIS usan longitud antes que latitud.

## Riesgo de contrato que M4 debe resolver primero

`staging.cafe_records` tiene `UNIQUE (run_id, source_id)`, pero M2 conserva los duplicados posteriores como filas rechazadas con el mismo `source_id` del primer registro. Insertar todas las filas de `TransformationResult.records` chocará con esa constraint.

Antes del loader, crear una migración Flyway V2 que permita auditar duplicados rechazados y siga protegiendo identidades aceptadas. Una opción compatible es quitar la constraint de tabla y crear un índice único parcial sobre `(run_id, source_id)` solo cuando el estado sea `accepted` o `accepted_with_warning`. Añadir una prueba PostgreSQL que inserte el original y duplicados rechazados, y que compruebe que dos registros aceptados con la misma identidad no caben.

## Tarea y aceptación para M4

1. Resolver el conflicto de unicidad anterior con Flyway V2; nunca editar V1 ya aplicada.
2. Implementar una unidad de carga que reciba `ExtractionResult` y `TransformationResult` y escriba `meta.pipeline_runs`, `raw.overpass_snapshots`, todas las filas de staging y solo las aceptadas en analytics.
3. Mantener cada ejecución en una transacción. Si falla staging o analytics, no dejar una ejecución marcada como completada ni resultados parciales.
4. Hacer idempotente el upsert de analytics por `source_id`; volver a cargar el mismo run no debe duplicar objetos.
5. Añadir CLI/pipeline mínimo y métricas de aceptados, rechazados e insertados/actualizados.
6. Probar con PostGIS local: primera carga, repetición, duplicado fuente rechazado, rollback ante fallo y geometría/SRID. No llamar Overpass desde las pruebas.
7. Actualizar documentación y ejecutar Ruff, formato, suite Python y migraciones Flyway.

No expandir M4 a API o frontend. No agregar Alembic. Usa SQL versionado por Flyway para cambios de esquema y respeta el contrato de `docs/data_dictionary.md`.
