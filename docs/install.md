# Guía de instalación limpia

Ruta completa desde una máquina nueva hasta el mapa verificado. Los comandos y resultados de la sección final provienen de una ejecución real (2026-10-13).

## Prerrequisitos

- `git`
- Docker con Compose (el stack usa imágenes `postgis/postgis:17-3.5`, `redgate/flyway:13.6.0` y `nginx:1.27-alpine`)
- [`uv`](https://docs.astral.sh/uv/) con Python 3.13 (el proyecto exige `>=3.12,<3.14`)

## Instalación

```bash
git clone https://github.com/hectmor/zmg-cafe-etl.git
cd zmg-cafe-etl
uv sync --extra dev
```

No se necesita `.env`: Compose usa los valores por defecto de `compose.yaml` y `.env.example` solo documenta las variables disponibles (nunca pongas secretos reales en Git).

## Stack con Compose

```bash
POSTGRES_PORT=0 docker compose up -d db api frontend
POSTGRES_PORT=0 docker compose --profile migrate run --rm flyway
POSTGRES_PORT=0 docker compose --profile etl run --rm etl
```

- `POSTGRES_PORT=0` evita chocar con otro PostgreSQL del host: Docker asigna un puerto aleatorio a `db` mientras los servicios se comunican por `db:5432` internamente. Si el puerto 5432 está libre, puede omitirse.
- El perfil `migrate` aplica las migraciones Flyway de `db/migrations`; es idempotente y puede repetirse.
- El perfil `etl` ejecuta el pipeline contra el stack (por defecto el fixture determinista) y deja los snapshots raw en `data/raw/`. Modo live: `POSTGRES_PORT=0 docker compose --profile etl run --rm etl python -m zmg_cafes_etl --live`.

## Verificación

```bash
curl http://localhost:8000/health
curl http://localhost:8000/stats
curl http://localhost:8000/geojson/cafes
```

Abre `http://localhost:8080` en el navegador: el mapa debe mostrar los cafés con nombre, búsqueda por nombre y filtro por tipo de objeto.

## Pruebas y calidad

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Para incluir `tests/integration/test_load_postgis.py` y `test_api_postgis.py` (que truncan sus cuatro schemas antes de cada prueba), usa la base de pruebas descartable, **nunca** la de desarrollo — ver `docs/database.md` e issue #59:

```bash
TEST_POSTGRES_PORT=0 docker compose --profile test up -d test-db
TEST_POSTGRES_PORT=0 docker compose --profile test run --rm test-flyway
TEST_DB_PORT=$(docker compose port test-db 5432 | cut -d: -f2)
export ZMG_TEST_DATABASE_URL="postgresql://zmg_cafes:zmg_cafes_dev@localhost:${TEST_DB_PORT}/zmg_cafes_test"
uv run pytest tests/integration/test_load_postgis.py tests/integration/test_api_postgis.py
docker compose --profile test down test-db
```

Para `tests/integration/test_stack_compose.py` (que siembra datos reales contra el stack ya levantado, sin truncar nada), usa en cambio la base del propio stack y las URLs del servicio corriendo, en una invocación separada:

```bash
export ZMG_TEST_DATABASE_URL=postgresql://zmg_cafes:zmg_cafes_dev@localhost:<PUERTO_DE_DB>/zmg_cafes
export ZMG_STACK_API_URL=http://localhost:8000
export ZMG_STACK_FRONTEND_URL=http://localhost:8080
uv run pytest tests/integration/test_stack_compose.py
```

El `<PUERTO_DE_DB>` se consulta con `docker compose port db 5432` (o `docker port <proyecto>-db-1 5432`). No combines ambos bloques en una sola corrida de `uv run pytest` sin filtrar archivos: `ZMG_TEST_DATABASE_URL` no puede apuntar a la vez a la base descartable y a la del stack.

## Registro de validación limpia (2026-10-13)

Ejecución real desde un `git clone` limpio de la rama con el flujo Compose, en una máquina con Docker y `uv`:

```text
$ git clone -b feat/issue-21-compose-profiles https://github.com/hectmor/zmg-cafe-etl.git && cd zmg-cafe-etl
$ uv sync --extra dev
+ zmg-cafes-etl==0.1.0
$ uv run ruff check .
All checks passed!
$ uv run pytest -q
54 passed, 13 skipped
$ POSTGRES_PORT=0 docker compose up -d db api frontend
 Container ...-db-1 Healthy → ...-api-1 Healthy → ...-frontend-1 Started
$ POSTGRES_PORT=0 docker compose --profile migrate run --rm flyway
Successfully applied 2 migrations to schema "meta", now at version v2
$ POSTGRES_PORT=0 docker compose --profile etl run --rm etl
{"object_count": 4, "accepted": 4, "rejected": 0, "inserted": 4, "updated": 0}
$ curl http://localhost:8000/health
{"status": "ok", "database": "connected"}
$ curl http://localhost:8000/stats
{"total": 4, "with_name": 3, "without_name": 1, "by_object_type": {"node": 2, "relation": 1, "way": 1}, ...}
$ curl http://localhost:8000/geojson/cafes
{"type": "FeatureCollection", "features": [{"geometry": {"coordinates": [-103.344, 20.6736], ...
$ curl -o /dev/null -w "%{http_code}" http://localhost:8080/
200
```

## Operación

- Detener sin borrar datos: `docker compose stop`. No ejecutes `docker compose down -v` si quieres conservar el volumen `postgres_data`.
- Reiniciar el ciclo completo solo requiere repetir `up`, `migrate` y `etl`; `migrate` no reaplica versiones ya aplicadas.
- Respaldo y restauración del volumen `postgres_data`, con un procedimiento probado contra un proyecto Compose aislado: [`docs/operations.md`](operations.md).
