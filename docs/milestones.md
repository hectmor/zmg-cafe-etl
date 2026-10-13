# Milestones del proyecto

Este archivo es el punto de continuidad del proyecto. Cada milestone debe dejar el repositorio en un estado funcional, documentado y verificable.

## Estado general

```text
M0 Fundación                 COMPLETADO
M1 Contrato y extracción    COMPLETADO
M2 Transformación y calidad COMPLETADO
M3 PostgreSQL/PostGIS       COMPLETADO
M4 Carga idempotente        COMPLETADO
M5 API FastAPI              COMPLETADO
M6 Frontend Leaflet         COMPLETADO
M7 Compose e integración    COMPLETADO
M8 Hardening profesional    SIGUIENTE
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

**Estado:** completado.

Implementar staging, upserts, transacciones, ejecución de pipeline, métricas y estados de ejecución.

Entregables: migración `V2__partial_unique_accepted_identity.sql` (unicidad de identidad solo para aceptados, con rechazos auditables en staging), unidad de carga transaccional en `src/zmg_cafes_etl/load.py`, upsert idempotente de `analytics.cafes` por `source_id`, CLI con transformación y carga opcional, métricas de aceptados, rechazados, insertados y actualizados.

Validación al cerrar M4: Flyway aplicó y verificó las versiones 1 y 2 en PostgreSQL 17.5/PostGIS. Ruff OK, formato OK y 45 pruebas exitosas: 39 sin Internet y 6 de integración contra PostGIS (`ZMG_TEST_DATABASE_URL`) que cubren primera carga, recarga sin duplicados, duplicado rechazado con identidad aceptada única, rollback completo ante fallo, geometría SRID 4326 y geometría nula en rechazos. Demostración CLI con `--database-url` sobre la carga del fixture: 4 aceptados, 0 rechazados, 4 insertados.

## M5 — API FastAPI

**Estado:** completado.

Implementar health check, consulta de cafés, detalle, estadísticas, paginación y GeoJSON.

Entregables: paquete `api/` separado del ETL (`main.py`, `db.py`, `schemas.py`), endpoints `GET /health`, `GET /cafes`, `GET /cafes/{source_id}`, `GET /geojson/cafes` y `GET /stats`, paginación con `limit`/`offset` validada, respuestas GeoJSON con coordenadas `[longitude, latitude]` y acceso de solo lectura a la capa `analytics`.

Validación al cerrar M5: Ruff OK, formato OK y 60 pruebas exitosas — 47 sin BD (rutas con store simulado) y 13 de integración contra PostGIS que cargan el fixture con el loader y verifican health, listado, paginación, detalle, 404, GeoJSON y estadísticas. Smoke test con `python -m uvicorn api.main:app` sobre datos reales: health conectado, listado paginado, FeatureCollection con `[-103.344, 20.6736]` y stats `total: 4`. El cliente de pruebas usa `httpx2` porque Starlette 1.7 deprecó `httpx` en su TestClient.

## M6 — Frontend Leaflet

**Estado:** completado.

Implementar mapa, búsqueda, filtros, marcadores, estados de carga/error y atribución.

Entregables: cliente estático en `frontend/` (`index.html`, `app.js`, `style.css`) sin frameworks ni build, mapa Leaflet centrado en la ZMG, carga desde `/geojson/cafes`, búsqueda por nombre, filtro por `object_type`, marcadores con popup (nombre, identidad, método de geometría y tags), estados de carga/listo/error con mensaje accedible y atribución de OpenStreetMap, Overpass y Leaflet. La API habilita CORS para el origen `http://localhost:8080`.

Validación al cerrar M6: Ruff OK, formato OK y 67 pruebas exitosas — 54 sin BD (incluidas 6 estructurales del frontend y la prueba de CORS) y 13 de integración contra PostGIS. Smoke test servido real: `http.server 8080 --directory frontend` entrega `index.html` y `app.js`, y la API responde con `access-control-allow-origin: http://localhost:8080` y GeoJSON `[-103.344, 20.6736]`. Limitación: el renderizado en navegador (teselas, popups) no se verificó con navegador automatizado.

## M7 — Compose, integración y CI

**Estado:** completado.

Agregar servicios reproducibles, pruebas de integración, migraciones en CI y validación de instalación limpia. Alcance operativo únicamente: sin funcionalidad nueva en ETL, API ni frontend.

Entregables, cada uno en su rama con PR a `develop`: `Dockerfile` y servicios `api`/`frontend` en `compose.yaml` con healthchecks (issue #20, PR #25); perfil `etl` que documenta el flujo `up → migrate → etl → verificar` (issue #21, PR #27); 5 pruebas de integración contra el stack servido por Compose en `tests/integration/test_stack_compose.py` — health, datos, GeoJSON, frontend y CORS (issue #23, PR #28); `docs/install.md` con el registro de una instalación limpia real desde `git clone` (issue #24, PR #29); `.github/workflows/ci.yml` con los jobs `quality` e `integration` sobre PostgreSQL/PostGIS efímero migrado con Flyway (issue #22, PR #30).

Validación al cerrar M7: Ruff OK, formato OK y 54 pruebas exitosas sin BD (18 omitidas sin variables de entorno: 13 de integración contra PostGIS y 5 del stack servido). Con el stack levantado y `ZMG_TEST_DATABASE_URL`/`ZMG_STACK_API_URL`/`ZMG_STACK_FRONTEND_URL` definidas, la sesión que cerró M7 registró las 13 pruebas de integración y las 5 del stack en verde, además de los jobs `quality` e `integration` del PR #30 en verde; detalle completo en `docs/handoff.md` §5.

## M8 — Hardening profesional

**Estado:** siguiente milestone.

Agregar observabilidad ligera, frescura, rendimiento, respaldo, recuperación y evaluación de ingesta incremental.

## Punto de reanudación

Para continuar el desarrollo:

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

La siguiente tarea es **M8 — Hardening profesional**. Lee primero `docs/handoff.md`, `AGENTS.md`, `docs/roadmap.md` y `docs/database.md`. El alcance (observabilidad ligera, frescura, rendimiento, respaldo, recuperación y evaluación de ingesta incremental) todavía no tiene criterios de aceptación detallados por fase; defínelos antes de delegar tareas a los especialistas.
