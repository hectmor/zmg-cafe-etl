# Milestones del proyecto

Este archivo es el punto de continuidad del proyecto. Cada milestone debe dejar el repositorio en un estado funcional, documentado y verificable.

## Estado general

```text
M0 Fundación                 COMPLETADO
M1 Contrato y extracción    COMPLETADO
M2 Transformación y calidad COMPLETADO
M3 PostgreSQL/PostGIS       COMPLETADO
M4 Carga idempotente        SIGUIENTE
M5 API FastAPI              PENDIENTE
M6 Frontend Leaflet         PENDIENTE
M7 Compose e integración    PENDIENTE
M8 Hardening profesional    PENDIENTE
```

## M0 — Fundación del repositorio

**Estado:** completado.

Entregables: estructura inicial, `pyproject.toml`, `uv.lock`, `requirements.txt`, configuración de calidad, documentación, fixture determinista, workflow multiagente y convenciones de commits.

## M1 — Contrato y extracción raw

**Estado:** completado.

Entregables: configuración tipada, validación del bounding box, consulta Overpass, extracción offline, extracción live preparada con timeout y reintentos, `run_id`, hash de consulta, snapshots raw, metadatos, prevención de sobrescritura, CLI y pruebas deterministas.

Demostración:

```bash
python -m zmg_cafes_etl \
  --offline tests/fixtures/overpass_cafes_sample.json \
  --raw-root /tmp/zmg-cafes-raw
```

Validación registrada al cerrar M1: Ruff OK, formato OK y 9 pruebas exitosas. La extracción live todavía no se ha ejecutado contra Overpass; sus solicitudes se cubren con pruebas simuladas.

## M2 — Transformación y calidad de datos

**Estado:** completado.

Objetivo: convertir objetos raw de Overpass en registros normalizados y separar aceptados, advertencias y rechazados.

Archivos previstos:

```text
src/zmg_cafes_etl/models.py
src/zmg_cafes_etl/validate.py
src/zmg_cafes_etl/transform.py
tests/unit/test_transform.py
tests/unit/test_validate.py
```

Entregables:

- modelos tipados del contrato normalizado;
- `object_type`, `object_id` y `source_id` canónico;
- coordenadas para `node` y `center` para `way`/`relation`;
- normalización de nombres y tags;
- validación de coordenadas;
- estados `accepted`, `accepted_with_warning` y `rejected`;
- razones estructuradas de rechazo;
- deduplicación determinista;
- tratamiento de registros fuera del área;
- fixture ampliado y pruebas sin Internet.

Criterios de aceptación:

- ningún registro aceptado tiene identidad o coordenadas inválidas;
- los nombres ausentes producen advertencia, no rechazo automático;
- no se inventan timestamps de modificación;
- una identidad fuente duplicada se resuelve de forma determinista;
- cada rechazado conserva una razón inspeccionable;
- todas las pruebas, Ruff y formato pasan.

Validación al cerrar M2: Ruff OK, formato OK y 31 pruebas exitosas sin Internet. La transformación se expone como biblioteca; su persistencia y orquestación CLI forman parte de los milestones posteriores.

## M3 — PostgreSQL y PostGIS

**Estado:** completado.

Crear schemas, migraciones Flyway, constraints, claves únicas, geometría `Point SRID 4326` e índices GiST.

Entregables: Compose con PostgreSQL 17/PostGIS y Flyway, migración `V1__initial_geospatial_schema.sql`, schemas `meta`, `raw`, `staging` y `analytics`, constraints del contrato normalizado e índices espaciales GiST.

Validación: Flyway aplicó y verificó la versión 1 en PostgreSQL 17.5; las geometrías de staging y analytics usan SRID 4326 y sus índices GiST existen. Ruff OK, formato OK y 33 pruebas exitosas. El puerto 5432 y 5433 estaban ocupados localmente; la comprobación se hizo con `POSTGRES_PORT=0`, que asigna un puerto aleatorio al host.

## M4 — Carga idempotente y pipeline

**Estado:** pendiente de M3.

Implementar staging, upserts, transacciones, ejecución de pipeline, métricas y estados de ejecución.

## M5 — API FastAPI

**Estado:** pendiente de M4.

Implementar health check, consulta de cafés, detalle, estadísticas, paginación y GeoJSON.

## M6 — Frontend Leaflet

**Estado:** pendiente de M5.

Implementar mapa, búsqueda, filtros, marcadores, estados de carga/error y atribución.

## M7 — Compose, integración y CI

**Estado:** pendiente de M4 y M5.

Agregar servicios reproducibles, pruebas de integración, migraciones en CI y validación de instalación limpia.

## M8 — Hardening profesional

**Estado:** pendiente del MVP.

Agregar observabilidad ligera, frescura, rendimiento, respaldo, recuperación y evaluación de ingesta incremental.

## Punto de reanudación

Para continuar el desarrollo:

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

La siguiente tarea es **M4 — Carga idempotente y pipeline**. Lee primero `docs/handoff.md`, `AGENTS.md`, `docs/project-spec.md`, `docs/data_dictionary.md`, `docs/database.md`, la migración inicial y `src/zmg_cafes_etl/{extract,transform,models}.py`.
