# Roadmap y definición de terminado

El estado operativo detallado y el punto de reanudación están en [milestones.md](milestones.md).

## Milestones

| Milestone | Entregable | Estado |
|---|---|---|
| 0 | Fundación, convenciones, arquitectura y configuración | Completado |
| 1 | Fuente Overpass, contrato y extracción offline/live | Completado |
| 2 | Validación y transformación con rechazados | Completado |
| 3 | PostGIS y migraciones Flyway | Completado |
| 4 | Carga idempotente y pipeline | Completado |
| 5 | API FastAPI y contrato GeoJSON | Completado |
| 6 | Frontend Leaflet | Completado |
| 7 | Compose reproducible, integración y CI | Completado |
| 8 | Observabilidad y hardening | Completado |

## Definition of Done

Un milestone no termina por crear archivos: debe tener documentación actualizada, pruebas relevantes ejecutadas y limitaciones declaradas. El MVP completo requiere fuente reproducible, snapshots raw, transformación validada, carga idempotente, PostGIS, API, frontend, pruebas y comandos de operación documentados.

## Dependencias

El contrato de fuente precede a la transformación; transformación precede al esquema staging/analytics; base de datos precede a API; API precede a frontend. Municipalidades quedan bloqueadas hasta identificar límites confiables.
