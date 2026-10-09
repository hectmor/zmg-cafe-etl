# Propuesta de arquitectura

## Propósito

El sistema separa adquisición, calidad, persistencia y consumo para que cada paso sea observable y pueda explicarse de manera independiente.

```mermaid
flowchart LR
  OSM[OpenStreetMap] --> OV[Overpass API]
  OV --> E[Extractor]
  E --> R[(Raw snapshots)]
  R --> T[Validate + transform]
  T --> S[(staging)]
  S --> L[Idempotent loader]
  L --> A[(analytics/PostGIS)]
  A --> API[FastAPI]
  API --> UI[Leaflet frontend]
```

La base de datos tendrá capas lógicas `raw`, `staging`, `analytics` y `meta`. El checkpoint actual solo define la fuente y no crea aún esas capas.

## Arquitectura lógica versus despliegue físico

La arquitectura lógica muestra responsabilidades y flujo de datos, sin afirmar procesos o contenedores concretos. El diagrama físico futuro mostrará contenedores Compose para PostGIS, ETL, API y servidor frontend; no se implementa todavía para evitar infraestructura antes del contrato.
