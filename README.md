<p align="center">
  <h1 align="center">☕ ZMG Cafés ETL</h1>
  <p align="center">A geospatial ETL pipeline for cafés, neverías and refresquerías in the Guadalajara Metropolitan Area</p>
  <p align="center">by <strong>Hector Moreno</strong></p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12%20%7C%203.13-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/PostgreSQL%2017-PostGIS-336791?style=flat-square&logo=postgresql&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square"/>
</p>

---

## What is this?

`zmg-cafes-etl` is an educational, portfolio-grade geospatial ETL pipeline. It turns public data
about cafés, neverías and refresquerías in the nine municipalities of the Guadalajara Metropolitan
Area (ZMG) into validated, queryable, map-ready data — end to end, with every stage documented and
tested before the next one was built.

| Stage | What it does |
|---|---|
| **Extract** | Pulls raw records from OpenStreetMap/Overpass and INEGI DENUE, and preserves an immutable snapshot of each run |
| **Transform** | Validates identity and geometry, classifies establishment type, and separates accepted records from rejected ones with an explicit reason |
| **Load** | Persists one run per transaction into PostgreSQL/PostGIS with an idempotent upsert — re-running never duplicates data |
| **API** | Serves the deduplicated data as JSON/GeoJSON through FastAPI |
| **Map** | A static Leaflet page that searches, filters and displays every establishment |

Everything runs on WGS84/SRID 4326, with coordinates in GeoJSON `[longitude, latitude]` order, and
every record carries a canonical identity `source:object_type:object_id` so a later run can update
it instead of duplicating it.

---

## Architecture

```mermaid
flowchart LR
    OSM["OpenStreetMap\n(Overpass API)"] --> EX["extract.py\nextract_denue.py"]
    DENUE["INEGI DENUE API"] --> EX
    EX -->|generic element\n{type, id, tags}| TR["transform.py\nvalidate + classify"]
    TR -->|accepted| LD["load.py\nupsert, one transaction"]
    TR -->|rejected| ST[("staging.cafe_records\naudit trail")]
    LD --> PG[("PostgreSQL + PostGIS\nanalytics.establecimientos")]
    PG -->|GeoJSON| API["FastAPI"]
    API --> MAP["Leaflet map"]
```

Two sources feed the same pipeline. OpenStreetMap is filtered to `amenity=cafe`, so every record
from it is a café by construction. INEGI DENUE is queried per municipality under SCIAN class
`722515`, which groups cafeterías, neverías, fuentes de sodas and refresquerías into a single
class — so a keyword heuristic (`classify.py`) recovers a likely subtype, explicitly documented as
a derived guess, never as official INEGI data. Rejected records are never discarded: they stay in
`staging` for audit, they just never reach `analytics`.

---

## Tech stack

**Data & extraction**
- **Python** — implements the whole ETL with the standard library (`urllib` for HTTP, no extra dependency for requests)
- **OpenStreetMap / Overpass API** — the simplest source: one query, `amenity=cafe`, inside the ZMG bounding box
- **INEGI DENUE API** — the official source: paged per municipality, filtered by SCIAN `722515`

**Storage**
- **PostgreSQL** — the four schemas (`meta`, `raw`, `staging`, `analytics`); transactions and constraints keep a load from ever landing half-written
- **PostGIS** — stores every establishment as a real geometry (`ST_MakePoint`) instead of two numeric columns, so spatial queries run directly in SQL
- **Flyway** — versions and applies every migration reproducibly; nobody runs an `ALTER` by hand

**Backend & frontend**
- **FastAPI** — serves `analytics.establecimientos` and `meta.pipeline_runs` as JSON/GeoJSON, with Pydantic response models
- **Leaflet** — draws the map from `/geojson/cafes` over OpenStreetMap tiles, no build step

**Development & operations**
- **Docker Compose** — orchestrates `db`, `flyway`, `etl`, `api` and `frontend` as independent profiles
- **uv** — manages the Python environment and dependencies with a lockfile
- **pytest** — unit and integration tests, including a disposable test-database profile
- **ruff** — lint and formatting
- **Claude Code multi-agent workflow** — a Lead Engineer session delegates scoped, file-owned contracts to specialist subagents (`.claude/agents/`); see [`docs/agent-workflows/`](docs/agent-workflows/)

No frontend framework, distributed system, orchestrator or cloud service gets added without a
concrete, documented need.

---

## Quickstart

### With Docker (recommended)

```bash
git clone https://github.com/hectmor/zmg-cafe-etl.git
cd zmg-cafe-etl

POSTGRES_PORT=0 docker compose up -d db api frontend
POSTGRES_PORT=0 docker compose --profile migrate run --rm flyway
POSTGRES_PORT=0 docker compose --profile etl run --rm etl
```

`POSTGRES_PORT=0` avoids clashing with a local Postgres; Docker assigns a random host port while
the services talk to each other over `db:5432`. Then:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/stats
```

Open `http://localhost:8080` for the map. Stop with `docker compose stop` — never `down -v`, which
deletes the `postgres_data` volume.

The full guide, including a real clean-install walkthrough, is in [`docs/install.md`](docs/install.md).

### Manual (local)

Requirements: Python 3.12 or 3.13, `uv`, Git.

```bash
uv sync --extra dev
uv run pytest
python -m zmg_cafes_etl --offline tests/fixtures/overpass_cafes_sample.json
```

Add `--database-url postgresql://zmg_cafes:zmg_cafes_dev@localhost:5432/zmg_cafes` to also
transform and persist the run. Serve the API and the frontend separately:

```bash
DATABASE_URL=postgresql://zmg_cafes:zmg_cafes_dev@localhost:5432/zmg_cafes \
  python -m uvicorn api.main:app --reload
python -m http.server 8080 --directory frontend
```

---

## Project structure

```
.
├── src/zmg_cafes_etl/     # ETL pipeline: config, extract, validate, classify, transform, load
├── api/                   # FastAPI service — reads only the analytics schema
├── frontend/              # Static Leaflet map, no build step
├── db/migrations/         # Flyway SQL migrations — never run by hand
├── config/sources.yaml    # Source configuration (bbox, endpoints, no secrets)
├── tests/                 # Unit and integration tests, deterministic fixtures
├── docs/                  # Architecture, ADRs, roadmap, operations, data dictionary
└── .claude/agents/        # Claude Code specialist subagent definitions
```

---

## Environment variables

| Variable | Description | Required |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | to persist a run or serve the API |
| `INEGI_DENUE_TOKEN` | DENUE API token (secret) | only for `--live` with the `inegi_denue` source |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_PORT` | Compose database defaults | no — already set in `compose.yaml` |
| `API_PORT` / `FRONTEND_PORT` | Compose service ports | no — already set in `compose.yaml` |

`INEGI_DENUE_TOKEN` must only ever live in a local `.env` file (gitignored); it is never written to
`config/sources.yaml` or printed to logs.

---

## Learn more

Everything below lives in `docs/` and is written in Spanish:

- [Project specification](docs/project-spec.md) — the shared data contract
- [Roadmap](docs/roadmap.md) and [milestones](docs/milestones.md) — what's done, what's next
- [Architecture overview](docs/architecture/overview.md) and [data flow](docs/architecture/data_flow.md)
- [Database and migrations](docs/database.md)
- [Data sources](docs/data_sources.md) and [data dictionary](docs/data_dictionary.md)
- [Operations: backup and restore](docs/operations.md)
- [Architectural decisions](docs/decisions/)
- [Multi-agent workflow](docs/agent-workflows/architecture.md)
- [Commit convention](docs/convencion-commits.md)
- [Known limitations](docs/limitations.md)

---

## Author

**Hector Moreno**

- GitHub: [@hectmor](https://github.com/hectmor)
- Email: [h.morenocarrion@gmail.com](mailto:h.morenocarrion@gmail.com)

## License

Code is distributed under the [MIT License](LICENSE).

Data derived from OpenStreetMap keeps the attribution and licensing obligations of OpenStreetMap
and the ODbL. Data derived from INEGI DENUE keeps INEGI's open-data attribution requirements.
