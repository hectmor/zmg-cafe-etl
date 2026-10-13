# Base de datos y migraciones

La base local usa PostgreSQL 17 con PostGIS y Flyway. Las migraciones versionadas están en `db/migrations`; Flyway registra su historial en el schema `meta`.

## Inicio local

```bash
docker compose up -d db
docker compose --profile migrate run --rm flyway
```

Para consultar el estado de las migraciones:

```bash
docker compose --profile migrate run --rm flyway info
```

La migración inicial crea los schemas `meta`, `raw`, `staging` y `analytics`, junto con geometrías `Point` en SRID 4326 e índices GiST. La migración `V2__partial_unique_accepted_identity.sql` sustituye la unicidad total de `(run_id, source_id)` en staging por un índice único parcial: las filas aceptadas siguen siendo únicas por ejecución y los rechazos por identidad duplicada quedan auditables. La migración `V3__analytics_cafes_stats_indexes.sql` agrega dos índices B-tree de una sola columna sobre `analytics.cafes(object_type)` y `analytics.cafes(geometry_method)`, exclusivamente para acelerar los `GROUP BY` de `AnalyticsStore.stats()` (ver "Rendimiento (M8.2)" abajo). El loader de `src/zmg_cafes_etl/load.py` escribe cada ejecución en una sola transacción: `meta.pipeline_runs`, `raw.overpass_snapshots`, todas las filas de `staging.cafe_records` y solo las aceptadas en `analytics.cafes` mediante upsert idempotente por `source_id`.

## Observabilidad y frescura (M8.1)

`GET /runs` expone, de solo lectura, las últimas ejecuciones registradas en `meta.pipeline_runs` (`run_id`, `source`, `status`, `started_at`, `completed_at`, con `limit` validado entre 1 y 100) y una frescura derivada: `last_completed_at` y `seconds_since_last_completed`. Ambos campos quedan en `null` cuando todavía no hay ninguna ejecución con `status = 'completed'`; nunca se fabrica un valor. `api/db.py` implementa `AnalyticsStore.list_runs` sobre la misma conexión de solo lectura que el resto de la capa; `api/schemas.py` calcula la frescura en `freshness_from_rows` a partir de las filas reales, no de un reloj interno de la base.

## Rendimiento (M8.2)

Las cuatro consultas de `AnalyticsStore` en `api/db.py` (`list_cafes`, `get_cafe`, `count_cafes`, `stats`) se validaron con `EXPLAIN (ANALYZE, BUFFERS)` real contra PostgreSQL 17.5/PostGIS, no con estimaciones del planner. Con solo las 4 filas del fixture de demo, Postgres prefiere correctamente un Seq Scan (una tabla tan chica nunca justifica un índice), así que la validación se hizo cargando 40,000 filas **sintéticas de benchmark** directamente por SQL en `analytics.cafes` (`source = 'benchmark'`, `source_id = 'benchmark:node:<n>'`, coordenadas aleatorias en un rango WGS84 válido dentro de la ZMG, `geometry` con `ST_SetSRID(ST_MakePoint(lon, lat), 4326)`, un `run_id` de benchmark fijo insertado en `meta.pipeline_runs`). Estas filas **no son datos reales de café**; se insertaron, se midieron y se borraron por completo en la misma sesión, sin tocar el fixture real ni `staging.cafe_records`.

Hallazgos con 40,004 filas (`ANALYZE analytics.cafes` ejecutado antes de medir):

| Consulta (`api/db.py`) | Plan real | Índice usado | Tiempo de ejecución |
|---|---|---|---|
| `list_cafes` (`ORDER BY source_id LIMIT/OFFSET`) | `Limit` → `Index Scan using cafes_pkey` | PK única de `source_id` | 0.057 ms |
| `get_cafe` (`WHERE source_id = ...`) | `Index Scan using cafes_pkey` | PK única de `source_id` | 0.024 ms |
| `count_cafes` (`SELECT count(*)` sin filtro) | `Aggregate` → `Seq Scan` | ninguno (ver nota) | 5.5 ms |
| `stats()` — totales con `FILTER (WHERE name ...)` | `Aggregate` → `Seq Scan` | ninguno (necesita la columna `name`, no indexada) | 7.7 ms |
| `stats()` — `GROUP BY object_type` | antes de V3: `Sort` → `HashAggregate` → `Seq Scan` (11.1 ms) | ninguno | 11.1 ms |
| `stats()` — `GROUP BY geometry_method` | antes de V3: `Sort` → `HashAggregate` → `Seq Scan` (13.0 ms) | ninguno | 13.0 ms |

`list_cafes` y `get_cafe` ya usaban el índice único de `source_id` (la clave primaria de `analytics.cafes`); no hicieron falta cambios. `count_cafes` y las dos agregaciones por `FILTER` de `stats()` hacen `Seq Scan` porque no tienen predicado selectivo: deben leer todas las filas sin importar qué índice exista, así que ese `Seq Scan` **no es evitable** y no se considera un cuello de botella.

Los dos `GROUP BY` de `stats()` (`object_type`, `geometry_method`) sí mostraron una mejora real y medible: se probó experimentalmente un índice B-tree de una sola columna sobre cada uno (creado, medido y eliminado antes de decidir) y el planner cambió de `Seq Scan` + `HashAggregate` a `Index Only Scan` + `GroupAggregate`, bajando de ~11-13 ms a ~4-8 ms sobre 40,004 filas. Se formalizó esa mejora en la migración `V3__analytics_cafes_stats_indexes.sql` (índices `analytics_cafes_object_type_idx` y `analytics_cafes_geometry_method_idx`), aplicada con Flyway (`docker compose --profile migrate run --rm flyway migrate`) y reconfirmada después con `EXPLAIN ANALYZE`: ambos `GROUP BY` usan ahora `Index Only Scan`, y como efecto colateral `count_cafes` también pasó a usar `Index Only Scan` sobre `analytics_cafes_object_type_idx` (el índice más chico disponible), en vez de `Seq Scan`.

Limitación honesta: a la escala real de este proyecto (cafés de un área metropolitana, probablemente cientos o pocos miles de filas, nunca 40,000), la diferencia absoluta es de pocos milisegundos y no representa un problema operativo hoy. Se agregó la migración porque el criterio de aceptación de M8.2 pedía demostrar con `EXPLAIN ANALYZE` si el `GROUP BY` de `stats()` tenía un índice adecuado, y la evidencia mostró que no lo tenía y que agregarlo sí mejora el plan; no se tocaron `V1` ni `V2`.

Procedimiento de benchmark ejecutado (resumen; sin SQL manual no rastreado para el índice permanente — solo para los datos sintéticos, que se insertaron y borraron por completo):

```bash
# Carga sintética (psql), medición con EXPLAIN ANALYZE, limpieza con DELETE
# Migración real aplicada vía Flyway:
docker compose --profile migrate run --rm flyway info
docker compose --profile migrate run --rm flyway migrate
```

Verificación de limpieza tras el benchmark:

```sql
DELETE FROM analytics.cafes WHERE source = 'benchmark';       -- DELETE 40000
DELETE FROM meta.pipeline_runs WHERE run_id = '00000000-0000-4000-8000-000000000041'; -- DELETE 1
SELECT count(*) FROM analytics.cafes;  -- 4
SELECT source, count(*) FROM analytics.cafes GROUP BY source; -- openstreetmap | 4
```

## Pruebas de integración

Las pruebas de `tests/integration/` requieren un PostgreSQL/PostGIS accesible y se omiten si no hay URL configurada. Cada prueba limpia los cuatro schemas antes de ejecutarse, así que usa una base de desarrollo, nunca una productiva:

```bash
ZMG_TEST_DATABASE_URL=postgresql://zmg_cafes:zmg_cafes_dev@localhost:PUERTO/zmg_cafes \
  python -m pytest tests/integration
```

El loader también acepta DSN con sufijo de SQLAlchemy (`postgresql+psycopg://...`), como el `DATABASE_URL` de `.env.example`.

Las credenciales de desarrollo están en `.env.example`. Crea un archivo `.env` local para usar valores distintos. Si el puerto 5432 ya está ocupado, define otro `POSTGRES_PORT` y ajusta `DATABASE_URL` al mismo puerto.

Para detener el servicio sin borrar la base local, ejecuta `docker compose stop db`. No uses `docker compose down -v` para una pausa normal: `-v` elimina el volumen persistente. Procedimiento de respaldo/restauración probado: [`docs/operations.md`](operations.md).
