# Roadmap de ZMG Cafés ETL

## ¿Qué es este proyecto?

`zmg-cafes-etl` es un proyecto educativo y de portafolio sobre ingeniería de datos geoespaciales.

El proyecto transforma información pública de cafés ubicados en la Zona Metropolitana de Guadalajara, México, en datos estructurados, validados y consultables.

El flujo completo que se construirá es:

```text
OpenStreetMap / Overpass API
        ↓
Extracción de datos
        ↓
Almacenamiento de datos raw
        ↓
Validación y transformación
        ↓
PostgreSQL + PostGIS
        ↓
API con FastAPI
        ↓
Mapa web con Leaflet
```

La aplicación final permitirá consultar cafés, buscarlos por nombre, visualizar sus ubicaciones y analizar la información geográficamente.

## Objetivo

El objetivo principal es demostrar cómo convertir datos públicos y potencialmente incompletos en información útil, reproducible y auditable.

El proyecto busca responder:

> ¿Cómo se puede transformar información pública sobre cafés en datos geoespaciales confiables, consultables y útiles?

También pretende enseñar cómo funciona un proceso ETL, cómo se extraen datos desde una API pública, cómo se conservan los datos originales, cómo se validan y transforman registros, cómo se detectan duplicados y cómo se cargan datos de forma idempotente.

## Tecnologías

### Datos y extracción

- **Python:** lenguaje principal.
- **OpenStreetMap:** fuente pública y colaborativa de información geográfica.
- **Overpass API:** consultas sobre objetos de OpenStreetMap.
- **PyYAML:** configuración de fuentes y geografía.
- **Polars:** previsto para transformaciones tabulares donde aporte claridad o rendimiento.

### Almacenamiento

- **PostgreSQL:** base de datos relacional.
- **PostGIS:** extensión espacial de PostgreSQL.
- **Flyway:** migraciones de base de datos versionadas en SQL.
- **GeoJSON:** intercambio de geometrías entre API y frontend.

### Backend y frontend

- **FastAPI:** API REST y documentación OpenAPI.
- **Pydantic:** validación de esquemas.
- **HTML, CSS y JavaScript:** frontend.
- **Leaflet:** mapa interactivo.

### Desarrollo y operación

- **Docker y Docker Compose:** entorno reproducible.
- **pytest:** pruebas automatizadas.
- **Ruff:** formato y análisis estático de Python.
- **uv:** gestión reproducible de dependencias.
- **Git y GitHub:** control de versiones.
- **Codex multi-agent workflow:** coordinación de tareas de ETL, base de datos y calidad.

No se incorporarán frameworks frontend, sistemas distribuidos, orquestadores o servicios cloud sin una necesidad concreta y documentada.

## Estado actual

M1 extracción, M2 transformación, M3 PostgreSQL/PostGIS, M4 carga idempotente, M5 API FastAPI y M6 frontend Leaflet están completados. La carga escribe cada ejecución en una transacción sobre PostgreSQL 17/PostGIS con Flyway y upsert idempotente en la capa analítica; el CLI acepta `--database-url` para persistir. La API expone solo la capa `analytics` con health, consulta paginada, detalle, estadísticas y GeoJSON. El frontend consumible desde el navegador muestra el mapa, búsqueda, filtros, marcadores, estados de carga/error y atribución. La extracción live está implementada, pero no se prueba automáticamente contra Overpass.

## Roadmap

### Fase 0 — Fundación

Arquitectura, convenciones, pruebas, documentación y contrato inicial de datos.

### Fase 1 — Fuente de datos

Estudio de OpenStreetMap y Overpass API, consulta `amenity=cafe`, área provisional, atribución y limitaciones.

### Fase 2 — Extracción

Extractor HTTP con timeout, reintentos, validación, snapshots raw, metadatos y modo offline. La extracción offline ya está implementada.

### Fase 3 — Validación y transformación

Normalización de objetos `node`, `way` y `relation`, identidades estables, validación de coordenadas, duplicados y registros rechazados.

### Fase 4 — PostgreSQL y PostGIS

Docker Compose, esquemas `raw`, `staging`, `analytics` y `meta`, migraciones Flyway, constraints e índices espaciales.

### Fase 5 — Carga idempotente

Upserts, ejecución repetible, métricas, procedencia, transacciones y manejo de errores.

### Fase 6 — API

FastAPI, health checks, búsqueda, filtros, paginación, GeoJSON y documentación OpenAPI.

### Fase 7 — Frontend

Mapa Leaflet, marcadores, búsqueda, filtros, estados de carga/error y atribución.

### Fase 8 — Integración y CI

Docker Compose completo, pruebas de integración, validación de migraciones y GitHub Actions.

### Fase 9 — Hardening profesional

Logs estructurados, métricas de calidad, frescura, rendimiento, respaldos y evaluación de ingesta incremental.

## Convenciones geográficas

- Sistema de referencia: WGS84 / EPSG:4326.
- GeoJSON: `[longitude, latitude]`.
- Los objetos `node` usan sus coordenadas.
- Los objetos `way` y `relation` usan el centro entregado por Overpass cuando está disponible.
- La identidad de un objeto OSM no equivale necesariamente a la identidad de un negocio real.
- No se asignarán municipios hasta disponer de límites confiables y documentados.

## Instalación actual

Requisitos: Python 3.12 o 3.13, `uv` y Git.

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
python -m zmg_cafes_etl --offline tests/fixtures/overpass_cafes_sample.json
python -m zmg_cafes_etl --offline tests/fixtures/overpass_cafes_sample.json \
  --database-url postgresql://zmg_cafes:zmg_cafes_dev@localhost:5432/zmg_cafes
```

El segundo comando además transforma y persiste la ejecución en PostgreSQL/PostGIS e imprime las métricas de aceptados, rechazados, insertados y actualizados. Sin `--database-url` (o la variable `DATABASE_URL`) solo se extrae y transforma.

Para servir la API (solo capa `analytics`):

```bash
DATABASE_URL=postgresql://zmg_cafes:zmg_cafes_dev@localhost:5432/zmg_cafes \
  python -m uvicorn api.main:app --reload
```

Endpoints: `GET /health`, `GET /cafes` (paginado con `limit`/`offset`), `GET /cafes/{source_id}`, `GET /geojson/cafes` (FeatureCollection con coordenadas `[longitude, latitude]`) y `GET /stats`.

Para usar el frontend Leaflet, sirve la API como arriba y los archivos estáticos de `frontend/` en el puerto 8080 (origen permitido por CORS):

```bash
python -m http.server 8080 --directory frontend
```

Abre `http://localhost:8080` en el navegador. El mapa consulta `/geojson/cafes`, permite buscar por nombre, filtrar por tipo de objeto y ver el detalle de cada café en el marcador.

### Stack completo con Docker Compose

El pipeline completo (base, migraciones, API y frontend) se levanta de forma reproducible con Compose. Usa `POSTGRES_PORT=0` si otra base ocupa el puerto 5432 del host: Docker asigna un puerto aleatorio a `db` mientras los servicios se comunican internamente por `db:5432`.

```bash
POSTGRES_PORT=0 docker compose up -d db api frontend
POSTGRES_PORT=0 docker compose --profile migrate run --rm flyway
POSTGRES_PORT=0 docker compose --profile etl run --rm etl
```

1. `db` (PostGIS), `api` (puerto 8000) y `frontend` (puerto 8080) arrancan en orden gracias a los healthchecks.
2. El perfil `migrate` aplica las migraciones Flyway de `db/migrations` sobre la base del stack; es idempotente y puede repetirse.
3. El perfil `etl` ejecuta el pipeline contra el stack: por defecto lee el fixture determinista y persiste el resultado en `analytics` (los snapshots raw quedan en `data/raw/`). Para el modo live: `POSTGRES_PORT=0 docker compose --profile etl run --rm etl python -m zmg_cafes_etl --live`.
4. Verifica con `curl http://localhost:8000/health`, `curl http://localhost:8000/stats` y abriendo `http://localhost:8080`.

Para detener sin borrar datos: `docker compose stop`. No ejecutes `docker compose down -v` si quieres conservar el volumen `postgres_data`.

El fixture determinista se encuentra en [`tests/fixtures/overpass_cafes_sample.json`](tests/fixtures/overpass_cafes_sample.json).

## Documentación relacionada

- [Especificación del proyecto](docs/project-spec.md)
- [Roadmap detallado](docs/roadmap.md)
- [Milestones y punto de reanudación](docs/milestones.md)
- [Handoff para continuar el desarrollo](docs/handoff.md)
- [Arquitectura](docs/architecture/overview.md)
- [Flujo de datos](docs/architecture/data_flow.md)
- [Base de datos y migraciones](docs/database.md)
- [Fuentes de datos](docs/data_sources.md)
- [Diccionario de datos](docs/data_dictionary.md)
- [Decisiones arquitectónicas](docs/decisions/)
- [Workflow multiagente](docs/agent-workflows/architecture.md)
- [Convención de commits](docs/convencion-commits.md)
- [Limitaciones conocidas](docs/limitations.md)

## Autor

**Hector Moreno**

- GitHub: [@hectmor](https://github.com/hectmor)
- Correo: [h.morenocarrion@gmail.com](mailto:h.morenocarrion@gmail.com)

## Licencia

El código se distribuye bajo la licencia [MIT](LICENSE).

Los datos derivados de OpenStreetMap conservan las obligaciones de atribución y licencia aplicables a OpenStreetMap y a la ODbL.
