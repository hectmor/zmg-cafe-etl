# Operación: respaldo y restauración

Procedimiento manual (sin automatización, sin cron, sin servicio nuevo) para respaldar y restaurar el volumen `postgres_data` del stack de Compose. Cubre solo los schemas del proyecto (`meta`, `raw`, `staging`, `analytics`); PostGIS, `topology` y `tiger` los aporta la imagen `postgis/postgis:17-3.5` y no se respaldan.

## Advertencias

- `docker compose down -v` borra el volumen `postgres_data` de forma irreversible. Para pausar sin perder datos usa `docker compose stop`; `down` sin `-v` también conserva el volumen.
- `down -v` actúa sobre el proyecto Compose activo. Sin `-p` explícito, ese proyecto es el nombre del directorio (`zmg-cafe-etl`), es decir, el stack real. Para practicar el procedimiento usa siempre un proyecto aislado (`-p zmg-cafe-backup-test` o similar) y confirma con `docker volume ls --filter label=com.docker.compose.project=<proyecto>` antes de destruir nada. No uses `export COMPOSE_PROJECT_NAME` mientras practiques: un `down -v` en otra terminal sin `-p` apuntaría al stack real.
- `pg_dump`/`pg_restore` deben correr con `-T` en `docker compose exec`; sin esa bandera, Compose asigna una TTY y corrompe la salida binaria del formato `-Fc`.
- Un respaldo no verificado no es un respaldo: valida siempre con `pg_restore --list` y comparando conteos/fingerprint antes de confiar en él.
- No ejecutes `flyway migrate` antes de restaurar sobre un stack limpio: el dump ya trae `meta.flyway_schema_history`, y Flyway fallaría o duplicaría el historial.
- El dump incluye `raw.overpass_snapshots` con el payload completo de Overpass; trátalo como cualquier otro dato del proyecto y nunca lo commitees. Guárdalo fuera del repositorio (`$HOME/zmg-cafe-backups` con `chmod 700`, por ejemplo). `.gitignore` ignora `*.dump`/`*.backup`/`/backups/` como red de seguridad adicional, no como sustituto.
- El destino debe ser la misma imagen (`postgis/postgis:17-3.5`) o al menos el mismo PostgreSQL mayor y PostGIS 3.x; el dump no incluye las extensiones.

## Respaldar

```bash
docker compose -p zmg-cafe-etl exec -T db sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-privileges -n meta -n raw -n staging -n analytics' \
  > "$HOME/zmg-cafe-backups/zmg_cafes-$(date +%Y%m%dT%H%M%S).dump"
```

Formato custom (`-Fc`): comprimido, inspeccionable con `pg_restore --list` y compatible con `--clean`/`--single-transaction` al restaurar. `--no-owner --no-privileges` permite restaurar aunque el usuario destino sea distinto. Solo se incluyen los 4 schemas del proyecto, no la base completa.

Validar el contenido del dump:

```bash
docker compose -p zmg-cafe-etl exec -T db pg_restore --list < "$HOME/zmg-cafe-backups/<archivo>.dump" | grep -E ' SCHEMA | TABLE DATA '
```

## Restaurar en un stack limpio

No ejecutes `flyway migrate` antes. Con el servicio `db` recién levantado y vacío:

```bash
docker compose -p zmg-cafe-etl exec -T db sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges --exit-on-error --single-transaction' \
  < "$HOME/zmg-cafe-backups/<archivo>.dump"
```

## Restaurar sobre una base que ya tiene los schemas

Agrega `--clean --if-exists`; sobrescribe únicamente los 4 schemas del proyecto (nunca PostGIS/tiger/topology):

```bash
docker compose -p zmg-cafe-etl exec -T db sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges --exit-on-error --single-transaction' \
  < "$HOME/zmg-cafe-backups/<archivo>.dump"
```

## Verificar

Compara conteos y un fingerprint de contenido antes/después (no solo el total de filas):

```sql
SELECT * FROM (
  SELECT 'analytics.cafes' AS k, count(*)::text AS v FROM analytics.cafes
  UNION ALL SELECT 'staging.cafe_records', count(*)::text FROM staging.cafe_records
  UNION ALL SELECT 'raw.overpass_snapshots', count(*)::text FROM raw.overpass_snapshots
  UNION ALL SELECT 'meta.pipeline_runs', count(*)::text FROM meta.pipeline_runs
  UNION ALL SELECT 'meta.flyway_schema_history', count(*)::text FROM meta.flyway_schema_history
  UNION ALL SELECT 'analytics.cafes.fingerprint', md5(coalesce(string_agg(source_id || '|' || ST_AsEWKT(geometry) || '|' || coalesce(name, ''), ',' ORDER BY source_id), '')) FROM analytics.cafes
) t ORDER BY k;
```

Y confirma que Flyway ve el schema restaurado como actualizado:

```bash
docker compose -p zmg-cafe-etl --profile migrate run --rm flyway info
```

## Probar el procedimiento sin arriesgar el stack real

Nunca practiques `down -v` contra el proyecto real. Usa un proyecto Compose aislado, con su propio volumen y contenedores:

```bash
# Stack de prueba, solo db, puerto aleatorio para no chocar con el real
POSTGRES_PORT=0 docker compose -p zmg-cafe-backup-test up -d --wait db
POSTGRES_PORT=0 docker compose -p zmg-cafe-backup-test --profile migrate run --rm flyway
POSTGRES_PORT=0 docker compose -p zmg-cafe-backup-test --profile etl run --rm etl

# Respaldo, destrucción desechable (SOLO del proyecto de prueba) y restauración
docker compose -p zmg-cafe-backup-test exec -T db sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-privileges -n meta -n raw -n staging -n analytics' \
  > /tmp/zmg_cafes-test.dump

# Antes de destruir, confirma que SOLO aparecen recursos del proyecto de prueba:
docker compose -p zmg-cafe-backup-test ps -a --format '{{.Name}}'
docker volume ls --filter label=com.docker.compose.project=zmg-cafe-backup-test --format '{{.Name}}'

docker compose -p zmg-cafe-backup-test down -v
POSTGRES_PORT=0 docker compose -p zmg-cafe-backup-test up -d --wait db
docker compose -p zmg-cafe-backup-test exec -T db sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges --exit-on-error --single-transaction' \
  < /tmp/zmg_cafes-test.dump

# Limpieza completa del entorno de prueba, incluida la imagen construida para él
docker compose -p zmg-cafe-backup-test down -v --rmi local
```

## Registro de validación (2026-10-13)

Ejecutado end-to-end contra el stack real (`zmg-cafe-etl`, 4 cafés reales de fixture, migraciones V1-V3) y un proyecto aislado (`zmg-cafe-backup-test`):

- Conteos/fingerprint capturados antes de tocar nada: `analytics.cafes=4`, fingerprint `8210205ec92f671784d45f50e82266fe`.
- `pg_dump` del stack real validado con `pg_restore --list`: solo los schemas `meta`, `raw`, `staging`, `analytics` y sus `TABLE DATA`, sin PostGIS/tiger/topology.
- Ciclo completo en el proyecto aislado (`zmg-cafe-backup-test`): `up` → `migrate` (V1-V3) → `etl` (4 aceptados) → `pg_dump` → verificación de que solo existían recursos del proyecto de prueba → `down -v` → `up` limpio → `pg_restore` sin `--clean` → diff de conteos vacío → `flyway info`/`migrate` confirma "up to date" en V3 → `pg_restore --clean --if-exists` sobre la misma base → diff de conteos vacío.
- El dump del stack **real** se restauró también en el proyecto aislado y coincidió en conteos y fingerprint con el estado real capturado al inicio.
- Verificación final: el stack real (`zmg-cafe-etl`) no se detuvo ni se recreó en ningún momento (solo se usó `exec`, nunca `up`/`run`/`down` contra ese proyecto); sus conteos tras toda la prueba siguen siendo idénticos a los capturados al inicio, y `GET /stats` responde con los mismos 4 cafés.
- El proyecto de prueba y su volumen se eliminaron por completo al terminar (`down -v --rmi local`); no quedó ningún dump de prueba en disco, solo el respaldo real en `$HOME/zmg-cafe-backups` (fuera del repositorio).

## Fuera de alcance

No hay respaldo automático (cron, servicio adicional). Este documento solo cubre el procedimiento manual.
