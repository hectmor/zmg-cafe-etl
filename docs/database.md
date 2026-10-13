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

La migración inicial crea los schemas `meta`, `raw`, `staging` y `analytics`, junto con geometrías `Point` en SRID 4326 e índices GiST. La migración `V2__partial_unique_accepted_identity.sql` sustituye la unicidad total de `(run_id, source_id)` en staging por un índice único parcial: las filas aceptadas siguen siendo únicas por ejecución y los rechazos por identidad duplicada quedan auditables. El loader de `src/zmg_cafes_etl/load.py` escribe cada ejecución en una sola transacción: `meta.pipeline_runs`, `raw.overpass_snapshots`, todas las filas de `staging.cafe_records` y solo las aceptadas en `analytics.cafes` mediante upsert idempotente por `source_id`.

## Pruebas de integración

Las pruebas de `tests/integration/` requieren un PostgreSQL/PostGIS accesible y se omiten si no hay URL configurada. Cada prueba limpia los cuatro schemas antes de ejecutarse, así que usa una base de desarrollo, nunca una productiva:

```bash
ZMG_TEST_DATABASE_URL=postgresql://zmg_cafes:zmg_cafes_dev@localhost:PUERTO/zmg_cafes \
  python -m pytest tests/integration
```

El loader también acepta DSN con sufijo de SQLAlchemy (`postgresql+psycopg://...`), como el `DATABASE_URL` de `.env.example`.

Las credenciales de desarrollo están en `.env.example`. Crea un archivo `.env` local para usar valores distintos. Si el puerto 5432 ya está ocupado, define otro `POSTGRES_PORT` y ajusta `DATABASE_URL` al mismo puerto.

Para detener el servicio sin borrar la base local, ejecuta `docker compose stop db`. No uses `docker compose down -v` para una pausa normal: `-v` elimina el volumen persistente.
