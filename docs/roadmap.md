# Roadmap y definición de terminado

## Milestones

| Milestone | Entregable | Estado |
|---|---|---|
| 0 | Fundación, convenciones, arquitectura y configuración | En progreso |
| 1 | Fuente Overpass, contrato y extracción offline/live | Siguiente |
| 2 | Validación y transformación con rechazados | Planeado |
| 3 | PostGIS, migraciones y carga idempotente | Planeado |
| 4 | API FastAPI y contrato GeoJSON | Planeado |
| 5 | Frontend Leaflet | Planeado |
| 6 | Compose reproducible, integración y CI | Planeado |
| 7 | Observabilidad y hardening | Planeado |

## Definition of Done

Un milestone no termina por crear archivos: debe tener documentación actualizada, pruebas relevantes ejecutadas y limitaciones declaradas. El MVP completo requiere fuente reproducible, snapshots raw, transformación validada, carga idempotente, PostGIS, API, frontend, pruebas y comandos de operación documentados.

## Dependencias

El contrato de fuente precede a la transformación; transformación precede al esquema staging/analytics; base de datos precede a API; API precede a frontend. Municipalidades quedan bloqueadas hasta identificar límites confiables.
