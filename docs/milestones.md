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
M8 Hardening profesional    COMPLETADO
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

**Estado:** completado.

Endurecer operación y visibilidad del stack ya entregado (M1-M7). Alcance operativo únicamente: sin funcionalidad de negocio nueva en ETL, API ni frontend; la ingesta incremental solo se evalúa en esta fase, no se implementa.

### M8.1 — Observabilidad ligera y frescura (issue #40, completado — PR #46)

Exponer el estado y la frescura de las ejecuciones ETL sin herramientas externas, usando `meta.pipeline_runs`: endpoint de solo lectura con las últimas ejecuciones y el tiempo desde la última `completed`, más logging estructurado en el CLI/loader.

Criterios: el endpoint es de solo lectura; la frescura se calcula sobre datos reales (nunca fabricada si no hay ejecuciones); pruebas unitarias y al menos una de integración contra PostGIS; documentado en `docs/database.md` y `docs/project-spec.md`.

### M8.2 — Rendimiento (issue #41, completado — PR #47)

Confirmar con `EXPLAIN ANALYZE` real que las consultas de `api/db.py` usan los índices existentes (clave única `source_id`, índices GiST de `analytics.cafes`); si aparece un cuello de botella real, agregar un índice vía migración Flyway, nunca SQL manual no rastreado.

Criterios: el plan de ejecución real queda documentado en `docs/database.md`; cualquier índice nuevo está cubierto por una migración versionada.

### M8.3 — Respaldo y recuperación (issue #42, completado)

Procedimiento documentado y probado de `pg_dump`/restauración del volumen `postgres_data`: respaldo con datos cargados, destrucción desechable del stack, recreación, restauración y comparación de conteos de `analytics.cafes` antes/después.

Criterios: el procedimiento se ejecuta tal cual y reproduce los mismos conteos; ningún dump ni dato productivo se commitea.

Validación real (2026-10-13): respaldo y restauración probados tanto en un proyecto Compose aislado (`zmg-cafe-backup-test`, con ciclo completo `up → migrate → etl → dump → down -v → up → restore`, dos veces: sin `--clean` y con `--clean --if-exists`) como con el dump del stack real restaurado en ese mismo entorno aislado. Conteos y un fingerprint MD5 del contenido de `analytics.cafes` coincidieron en todos los casos (diff vacío). El stack real (`zmg-cafe-etl`) nunca se detuvo ni se recreó durante la prueba — solo se usó `exec`, nunca `up`/`run`/`down`. Detalle completo en `docs/operations.md`.

### M8.4 — Evaluación de ingesta incremental (issue #43, completado)

ADR-005 que compare la re-extracción completa actual (con deduplicación determinista de M2 y upsert idempotente de M4) contra filtros incrementales de Overpass (`newer`/`changed`), con una decisión explícita: adoptar, descartar o posponer. Sin implementación en este issue.

Criterios: ADR registrado en `docs/decisions/` siguiendo el formato de ADR-001 a ADR-004; decisión justificada y no dejada abierta.

Decisión (`docs/decisions/ADR-005-incremental-ingestion.md`): **descartar** la ingesta incremental mientras el bbox, el volumen y la ausencia de restricciones de cuota se mantengan como hoy. Verificado contra la documentación oficial de Overrpass QL/Augmented Diffs (citas en el ADR), no asumido. La investigación detectó un gap real no relacionado con la decisión en sí: `load_run` nunca retira de `analytics.cafes` los `source_id` que desaparecen de la fuente — registrado como issue #49, fuera de M8.

## Punto de reanudación

Para continuar el desarrollo:

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

M8 — Hardening profesional está completo (issues #40-#44, PRs #46-#48 y este). Queda abierto el issue #49 (`analytics.cafes` no retira cafés desaparecidos de la fuente), encontrado durante M8.4 pero fuera de su alcance. Todavía no hay un milestone M9 definido; antes de abrir uno nuevo, revisa `docs/roadmap.md` y decide con el Lead si el siguiente paso es #49, cerrar la deuda de `docs/agent-workflows/` (#18, #19) o un alcance nuevo.
