# Milestones del proyecto

Este archivo es el punto de continuidad del proyecto. Cada milestone debe dejar el repositorio en un estado funcional, documentado y verificable.

## Estado general

```text
M0 Fundación                 COMPLETADO
M1 Contrato y extracción    COMPLETADO
M2 Transformación y calidad SIGUIENTE
M3 PostgreSQL/PostGIS       PENDIENTE
M4 Carga idempotente        PENDIENTE
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

Validación: Ruff OK, formato OK, 9 pruebas exitosas. La extracción live todavía no se ha ejecutado contra Overpass.

## M2 — Transformación y calidad de datos

**Estado:** siguiente milestone.

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

## M3 — PostgreSQL y PostGIS

**Estado:** pendiente de M2.

Crear schemas, migraciones Alembic, constraints, claves únicas, geometría `Point SRID 4326` e índices GiST.

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

Para continuar desde otra laptop:

```bash
git clone https://github.com/hectmor/zmg-cafe-etl.git
cd zmg-cafe-etl
conda activate zmg-cafe
python -m pip install -r requirements.txt
pytest
```

La siguiente tarea es **M2 — Transformación y calidad de datos**. Antes de editar, leer `AGENTS.md`, `docs/project-spec.md`, `docs/data_dictionary.md`, este archivo, `config/sources.yaml` y `src/zmg_cafes_etl/extract.py`.
