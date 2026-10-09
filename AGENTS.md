# AGENTS.md

## Propósito

`zmg-cafes-etl` es un proyecto educativo de ETL geoespacial para cafés de la Zona Metropolitana de Guadalajara. Cada fase debe quedar documentada, reproducible y verificable; el objetivo es enseñar el ciclo completo de datos, no solo construir un mapa.

## Arquitectura y directorios

- `config/`: configuración no secreta de fuentes y geografía.
- `src/zmg_cafes_etl/`: extracción, validación, transformación, carga y pipeline.
- `api/`: capa FastAPI separada del ETL.
- `frontend/`: cliente Leaflet que consume la API.
- `data/`: snapshots y rechazos locales; no subir datos productivos.
- `docs/`: arquitectura, decisiones, tutoriales, calidad y operación.
- `tests/`: pruebas unitarias, de integración y fixtures deterministas.
- `docs/agent-workflows/`: protocolo de delegación, perfiles y ejercicios multiagente.

## Comandos

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Cuando existan migraciones, deben ejecutarse con Alembic y nunca mediante SQL manual no rastreado.

## Coordinación multiagente

El Lead Engineer conserva la responsabilidad de alcance, contratos, integración y aceptación. Los especialistas trabajan con tareas acotadas, archivos propietarios y criterios explícitos. No se delegan tareas dependientes antes de aceptar el contrato que comparten.

Cada entrega debe indicar archivos modificados, decisiones, comandos ejecutados, resultados reales, limitaciones, preguntas abiertas y posibles impactos en otros componentes. En un filesystem compartido no se permiten ediciones concurrentes del mismo archivo; para cambios paralelos use worktrees aislados o limite a los agentes a revisión de solo lectura.

El protocolo completo está en `docs/agent-workflows/task-protocol.md` y la práctica inicial en `docs/agent-workflows/first-exercise.md`.

## Reglas de desarrollo

- Inspeccionar el repositorio y el grafo de código antes de editar; preferir `search_graph`, `trace_path` y `get_code_snippet`.
- Mantener separación entre extracción, transformación, persistencia, HTTP y presentación.
- Usar type hints, funciones pequeñas y errores explícitos.
- La identidad de fuente es `source + object_type + object_id`; no confundirla con identidad del negocio.
- Rechazar coordenadas imposibles y distinguir rechazo, advertencia y campos opcionales ausentes.
- Usar WGS84/SRID 4326 y orden GeoJSON `[longitude, latitude]`.
- No fabricar nombres, límites municipales, timestamps de fuente ni conteos.
- Todo cambio de comportamiento requiere actualizar documentación y pruebas.
- Reportar comandos y resultados reales.
- No versionar `.env`, secretos, snapshots raw grandes ni artefactos generados.

## Reporte final obligatorio

Todo milestone debe cerrar con un resumen en español de alcance, archivos, decisiones, comandos y resultados, criterios satisfechos, criterios pendientes y siguiente paso recomendado. Nunca presentar una capacidad planeada como implementada.
