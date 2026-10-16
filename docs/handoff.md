# Handoff y brief de auditoría

Documento autocontenido para que un modelo auditor (o el siguiente colaborador) entienda el estado del repo sin contexto adicional. Última actualización: **13 de octubre de 2026** (tras la sesión de M7).

## 1. Reglas de trabajo activas

- **Git:** una rama por issue (`tipo/issue-N-slug`) desde `develop`; cada PR va a `develop` y referencia `Closes #N`. Rama por fase quedó obsoleta (issue #18).
- **Metadata de PR:** assignee `hectmor`, label del issue, milestone correspondiente y proyecto GitHub `zmg-cafe`.
- **Migraciones:** solo Flyway (`db/migrations`, imágenes `redgate/flyway:13.6.0`). Prohibido Alembic y SQL manual no rastreado.
- **Commits:** inglés, formato de `docs/convencion-commits.md`, sin trailers de coautoría.
- **Contrato:** identidad `source + object_type + object_id`; `source_id = source:object_type:object_id`; WGS84/SRID 4326; GeoJSON `[longitude, latitude]`; no fabricar nombres, límites municipales, timestamps ni conteos.
- **Multiagente:** la sesión primaria (Lead) coordina a `etl-engineer`, `database-engineer` y `qa-data-quality-engineer` (`.opencode/agents/`, equivalente a los perfiles Codex de `docs/agent-workflows/profiles/`).

## 2. Dónde vive la verdad

| Tema | Fuente |
|---|---|
| Avance por milestone | `docs/milestones.md` (estados y validaciones) |
| Definición de terminado | `docs/roadmap.md` |
| Decisiones de diseño | `docs/decisions/` (ADR-001 fuente, ADR-002 snapshots raw, ADR-003 batch manual, ADR-004 contrato de registro) |
| Campos y estados | `docs/data_dictionary.md`, `docs/project-spec.md` |
| Esquema de base | `docs/database.md` + migraciones `db/migrations/` |
| Operación del stack | `docs/install.md`, este documento |
| Protocolo multiagente | `docs/agent-workflows/` |
| Convención de commits | `docs/convencion-commits.md` |

## 3. Estado del roadmap

M0–M6 **completados y documentados** (fundación, extracción Overpass, transformación/validación, PostGIS+Flyway, carga idempotente, API FastAPI, frontend Leaflet). **M7 (Compose, integración y CI) está implementado en PRs abiertos** (ver §4). M8 (hardening) pendiente. Detalle y validaciones: `docs/milestones.md`.

## 4. Estado de GitHub al 2026-10-13

**Milestones:** #1 `M4` cerrado · #2 `M5` cerrado · #3 `M7` abierto (issues #20–#24, todos con PR).

**PRs abiertos (todos a `develop`, assignee `hectmor`, milestone M7):**

| PR | Issue | Rama | Contenido | Estado |
|---|---|---|---|---|
| #25 | #20 | `feat/issue-20-compose-services` | `Dockerfile` API + servicios `api`/`frontend` en Compose con healthchecks | base del stack |
| #27 | #21 | `feat/issue-21-compose-profiles` | Perfil `etl` + flujo `up → migrate → etl → verificar` | apilado en #25 |
| #29 | #24 | `docs/issue-24-clean-install` | `docs/install.md` con registro de instalación limpia real | apilado en #27 |
| #28 | #23 | `feat/issue-23-compose-integration` | 5 pruebas del stack servido (health, datos, GeoJSON, frontend, CORS) | independiente |
| #30 | #22 | `feat/issue-22-ci-workflow` | `.github/workflows/ci.yml` (quality + integration con Flyway) | **CI verde** |

**Orden de merge:** #25 → #27 → #29; #28 y #30 en cualquier orden. Los apilados muestran también commits de sus dependencias hasta que se fusionen.

**Issues abiertos sin milestone:** #19 (verificar que los agentes opencode se usen) · #26 (bug: la API no acepta el DSN `postgresql+psycopg://` de `.env.example`) · #31 (este documento).

## 5. Verificación: comandos y resultados esperados

```bash
uv sync --extra dev          # Python 3.13 (pyproject exige >=3.12,<3.14)
uv run ruff check .          # All checks passed
uv run ruff format --check . # N archivos ya formateados
uv run pytest                # 54 passed, 13 skipped (sin BD; integración se omite)
```

Con una base migrada por Flyway y variables definidas, la suite completa pasa (67 pruebas: 54 sin BD + 13 de integración; con el PR #28 se suman 5 del stack):

```bash
export ZMG_TEST_DATABASE_URL=postgresql://zmg_cafes:zmg_cafes_dev@localhost:<PUERTO>/zmg_cafes
export ZMG_STACK_API_URL=http://localhost:8000        # solo con el stack levantado
export ZMG_STACK_FRONTEND_URL=http://localhost:8080   # solo con el stack levantado
uv run pytest
```

Resultado verificado hoy: 13/13 de integración y 5/5 del stack en verde; `pytest` sin variables: 54 passed. CI del PR #30: jobs `quality` e `integration` en verde. El flujo completo del stack (incluida una instalación limpia real desde `git clone`) está registrado en `docs/install.md`.

## 6. Entorno operativo

- **Stack Compose:** `db` (postgis/postgis:17-3.5), `flyway` (redgate/flyway:13.6.0, perfil `migrate`), `api` (imagen del `Dockerfile`, Python 3.13-slim + uvicorn), `frontend` (nginx:1.27-alpine). Servicio `etl` (perfil `etl`) ejecuta el pipeline contra el stack.
- **Puertos:** `api` 8000, `frontend` 8080 (orígenes CORS de la API), `db` 5432. Convención `POSTGRES_PORT=0` cuando el host ya usa 5432 (Docker asigna uno aleatorio; consultar con `docker compose port db 5432`).
- **Cuidados:** `docker compose stop` conserva datos; no ejecutar `down -v`; no ejecutar `docker compose run` sin `POSTGRES_PORT=0` si otro servicio ocupa 5432.
- **Variables:** `.env.example` solo documenta placeholders (nunca secretos en Git). `ZMG_TEST_DATABASE_URL`, `ZMG_STACK_API_URL` y `ZMG_STACK_FRONTEND_URL` solo para pruebas.
- **Python:** usar `uv` con 3.13. El entorno conda local `zmg-cafe` tiene 3.14.8 (fuera del rango de `pyproject.toml`); no usarlo como referencia.

## 7. Contrato de persistencia (resumen)

Esquemas: `meta.pipeline_runs` (ejecución), `raw.overpass_snapshots` (payload crudo), `staging.cafe_records` (aceptados y rechazados, con razón) y `analytics.establecimientos` (estado consultable por `source_id`). Geometría `Point, 4326` construida como `ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)`; nula en rechazos. Desde `V2`, la unicidad de `(run_id, source_id)` en staging aplica solo a aceptados (índice `staging_run_accepted_identity`); los duplicados rechazados quedan auditables. Detalle: `docs/database.md`, `docs/data_dictionary.md`.

## 8. Problemas conocidos y limitaciones

- **#26 (bug):** `api/db.py` conecta con `psycopg.connect` sin normalizar el sufijo `postgresql+psycopg://` que documentan `.env.example` y `docs/database.md`; con ese valor, `/health` queda en 503. El loader sí lo normaliza (`normalize_dsn`). Repro y aceptación en el issue.
- **#19 (sigue abierto, solo opencode):** los agentes opencode (`etl-engineer`, `database-engineer`, `qa-data-quality-engineer`) existen en `.opencode/agents/`, pero no se ha verificado que una sesión los cargue y use. El equivalente de Claude Code sí quedó verificado (ver más abajo); #19 queda acotado a opencode.
- **Claude Code — agentes verificados (2026-10-15):** una sesión headless nueva (`claude -p ...`) sobre el checkout con `.claude/agents/` sincronizado listó `database-engineer`, `etl-engineer` y `qa-data-quality-engineer` como `subagent_type` disponibles y pudo invocar `etl-engineer` con éxito (leyó `src/zmg_cafes_etl/extract.py` y reportó correctamente que `extract_live` hace la petición HTTP live a Overpass). Nota operativa: una sesión en curso no redescubre `.claude/agents/` si el archivo llega al working tree después de que la sesión ya inició (se necesita una sesión nueva).
- **#18 (resuelto):** `AGENTS.md`, `docs/agent-workflows/task-protocol.md` y `docs/agent-workflows/architecture.md` ya reflejan la convención vigente (rama por issue + metadata de PR, §1); "una rama por fase" quedó retirada de los tres documentos.
- **Renderizado en navegador** del frontend sin automatizar (solo verificación HTTP), heredado de M6.
- **Extracción live contra Overpass real nunca ejecutada** (M1); el modo live está cubierto con HTTP simulado.
- **Historia descartada:** hubo un intento local paralelo de M2–M4 con Alembic; está obsoleto y preservado como `stash@{0}` en la rama `main` de esta máquina. El camino válido es `develop` + Flyway. No mezclar.

## 9. Checklist de auditoría sugerida

- [ ] `docs/milestones.md` coincide con el código de `develop` (M1–M6) y las validaciones citadas son reproducibles.
- [ ] Migraciones Flyway: únicas, reversibles donde aplique y sin SQL manual fuera de `db/migrations`.
- [ ] Pruebas: cobertura de identidad, coordenadas, duplicados, rechazos con razón, idempotencia de carga y contrato de API/GeoJSON.
- [ ] Contrato: `source_id`, `[longitude, latitude]`, SRID 4326 y estados/razones según `docs/data_dictionary.md`.
- [ ] Seguridad: sin secretos en Git; API de solo lectura sobre `analytics`; CORS limitado a orígenes documentados; imágenes con versiones fijadas.
- [ ] Consistencia GitHub: cada PR referencia `Closes #N`, con assignee/label/milestone acordes a §1 y §4.
- [ ] Los comandos de `README.md`, `docs/install.md` y §5 se ejecutan tal cual y producen los resultados citados.
- [ ] Coherencia entre `compose.yaml`, `Dockerfile`, `.github/workflows/ci.yml` y esta documentación.
