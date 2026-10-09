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
- **Alembic:** migraciones de base de datos.
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

El proyecto se encuentra en la etapa de fundación y diseño del contrato de datos.

Actualmente existe:

- arquitectura inicial;
- configuración de OpenStreetMap/Overpass;
- contrato inicial de datos normalizados;
- fixture offline determinista;
- documentación de decisiones y limitaciones;
- workflow multiagente;
- configuración de Python, pytest y Ruff;
- extractor offline-first con snapshots raw y metadatos;
- comando CLI para ejecutar la extracción offline;
- pruebas de configuración, fixture y extracción.

Todavía no están implementadas la transformación, PostGIS, la API ni el frontend. La extracción live está preparada, pero no se valida automáticamente contra Overpass.

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

Docker Compose, esquemas `raw`, `staging`, `analytics` y `meta`, migraciones Alembic, constraints e índices espaciales.

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
```

El fixture determinista se encuentra en [`tests/fixtures/overpass_cafes_sample.json`](tests/fixtures/overpass_cafes_sample.json).

## Documentación relacionada

- [Especificación del proyecto](docs/project-spec.md)
- [Roadmap detallado](docs/roadmap.md)
- [Arquitectura](docs/architecture/overview.md)
- [Flujo de datos](docs/architecture/data_flow.md)
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
