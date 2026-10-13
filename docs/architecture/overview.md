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

La base de datos usa las capas lógicas `raw`, `staging`, `analytics` y `meta`. La migración inicial de Flyway crea sus tablas y constraints; M4 conectará la transformación con esa persistencia.

## Arquitectura lógica versus despliegue físico

Compose implementa el contenedor local de PostGIS y el servicio puntual de Flyway. Los contenedores de ETL, API y frontend siguen fuera de alcance hasta sus milestones.
