# Arquitectura del workflow multiagente

Estos agentes son roles de desarrollo coordinados por Codex; no son servicios productivos independientes.

## Roles

- **Lead Engineer:** define alcance, acepta contratos, asigna archivos, reconcilia propuestas, integra y publica el reporte.
- **ETL Engineer:** fuente, extracción, snapshots raw, normalización, validación, deduplicación y métricas.
- **Database Engineer:** esquema, PostGIS, migraciones, constraints, índices, upserts y SQL analítico.
- **QA/Data Quality Engineer:** criterios, casos límite, regresiones, consistencia y evidencia de pruebas.

## Flujo

```mermaid
flowchart LR
  R[Requisitos] --> L[Lead Engineer]
  L --> T[Tarea acotada + criterios]
  T --> E[Especialista]
  E --> I[Implementación o propuesta + pruebas]
  I --> V[Revisión Lead]
  V --> X{Contrato aceptado?}
  X -- No --> C[Corrección o aclaración]
  C --> E
  X -- Sí --> G[Integración]
  G --> A[Pruebas de aceptación]
  A --> F[Reporte en español]
```

## Paralelismo seguro

Pueden correr en paralelo revisiones read-only del contrato de fuente por ETL, DB y QA. No pueden correr en paralelo dos ediciones del mismo contrato, migración o archivo. La implementación de DB depende del contrato aceptado; API depende del esquema consumer-facing; frontend depende del contrato API.

## Interfaces y conflictos

Las interfaces se acuerdan primero en documentos versionados. Si una recomendación contradice otra, el Lead compara evidencia, impacto y criterios; no resuelve el conflicto ocultándolo en código. La decisión final se registra en un ADR o en la especificación del proyecto.

## Fallos

Un fallo de herramienta, red o dependencia se reporta como limitación reproducible. Un fallo de datos debe conservar rechazados y razones. Un test no ejecutado no se presenta como exitoso. El Lead puede reintentar una tarea, dividirla o detenerla, pero no relajar silenciosamente la aceptación.

## Capacidad real de Codex verificada

El CLI local `0.162.1` soporta perfiles TOML (`--profile`), worktrees (`--worktree`), sandbox read-only/workspace-write, sesiones y el feature estable `multi_agent`. La delegación dentro de esta sesión se realiza con las herramientas de subagentes del harness; el CLI local no expone un comando de “crear agente especialista” en `codex agents`. Por ello las instrucciones de rol viven en Markdown versionado y los TOML solo fijan configuración operacional.
