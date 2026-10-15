# Protocolo de tareas delegadas

## 1. Handoff obligatorio

Cada tarea debe incluir:

- **ID:** identificador único, por ejemplo `CONTRACT-001`.
- **Objetivo:** resultado observable.
- **Fase:** fase del roadmap.
- **Requisitos:** reglas y contratos aplicables.
- **Alcance:** trabajo incluido.
- **Exclusiones:** archivos, componentes o decisiones fuera del encargo.
- **Archivos autorizados:** lista explícita; si es revisión, ninguno.
- **Entregables:** documentos, código, pruebas o recomendaciones.
- **Aceptación:** condiciones comprobables.
- **Pruebas:** comandos que debe ejecutar el agente.
- **Dependencias:** tareas previas o paralelas.
- **Riesgos y supuestos:** incertidumbres que deben hacerse visibles.
- **Reporte:** formato de salida exigido.

## 2. Reporte del especialista

El agente debe informar:

1. archivos creados o modificados;
2. decisiones de diseño y alternativas descartadas;
3. comandos ejecutados y resultados reales;
4. limitaciones y preguntas abiertas;
5. efectos potenciales sobre otros contratos;
6. criterios de aceptación satisfechos y pendientes.

## 3. Propiedad de archivos

El Lead asigna un propietario por archivo. Solo un agente puede editar un archivo en una ronda. Las revisiones paralelas deben ser read-only. Si dos cambios son realmente independientes, usar worktrees separados y fusionar únicamente después de revisión del Lead.

Propiedad inicial:

| Área | Propietario primario | Revisor |
|---|---|---|
| `src/zmg_cafes_etl/extract.py`, `transform.py`, `validate.py` | ETL Engineer | QA |
| `migrations/`, `sql/`, repositorios DB | Database Engineer | QA |
| `tests/` y reportes de aceptación | QA Engineer | Lead |
| contratos, README y ADR | Lead | los tres especialistas |

La propiedad no autoriza modificar interfaces compartidas sin registrar una propuesta y obtener aceptación del Lead.

## 4. Cierre

El Lead revisa el diff real, ejecuta las pruebas de integración y actualiza la documentación. Un resumen del agente nunca sustituye la inspección del código ni la ejecución local.

## 5. Rama y pull request

Cada tarea delegada se implementa en una rama por issue (`tipo/issue-N-slug`) desde `develop`, nunca una rama por fase. El PR resultante va a `develop`, referencia `Closes #N` y lleva la metadata exigida en `AGENTS.md` (assignee `hectmor`, label del issue, milestone correspondiente, proyecto GitHub `zmg-cafe`).
