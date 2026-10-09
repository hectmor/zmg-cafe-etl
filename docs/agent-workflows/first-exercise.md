# Primer ejercicio: revisar el contrato de un café

## Objetivo

Usar tres revisiones especializadas antes de implementar código para aceptar un contrato común de registro de café.

## Contrato a revisar

| Campo | Requerido | Regla |
|---|---:|---|
| `source` | sí | `openstreetmap` |
| `object_type` | sí | `node`, `way` o `relation` |
| `object_id` | sí | ID positivo de OSM |
| `source_id` | sí | `source:object_type:object_id`, identidad estable del objeto |
| `name` | no | `tags.name`; puede ser nulo |
| `category` | sí | categoría consultada, inicialmente `cafe` |
| `latitude`, `longitude` | sí | WGS84; rangos válidos |
| `geometry` | sí para aceptados | punto normalizado SRID 4326; raw conserva el payload |
| `geometry_method` | sí para aceptados | `node_coordinates` o `overpass_center` |
| `tags` | sí | objeto raw; `{}` si falta |
| `retrieved_at` | sí | momento de adquisición |
| `run_id` | sí | UUID serializado de la ejecución |
| `validation_status` | sí en staging | `accepted`, `accepted_with_warning` o `rejected` |
| `rejection_reason` | solo rechazo | razón estructurada; nulo para aceptados |
| `source_updated_at` | no | solo si la fuente lo entrega; nunca inventar |
| `municipality` | no | no existe hasta contar con límites confiables |

## Cómo iniciarlo en Codex CLI

Los archivos de rol están en `docs/agent-workflows/agents/`. Los perfiles TOML son plantillas en `docs/agent-workflows/profiles/`; el CLI solo los carga desde `$CODEX_HOME/<name>.config.toml`, así que no se copian automáticamente ni se modifica la configuración global.

Después de copiar voluntariamente las plantillas a tu configuración de usuario, una ejecución read-only de revisión tiene esta forma:

```bash
codex exec --profile zmg-qa --sandbox read-only -C /home/iieg/Documents/datzin/zmg-cafe-etl -
```

Pega como entrada la tarea con ID `CONTRACT-001` y la instrucción de leer `AGENTS.md`, `docs/project-spec.md`, `config/sources.yaml` y este ejercicio; no modificar archivos.

Para una implementación ETL posterior se usaría `zmg-etl` con `--sandbox workspace-write`, y para DB `zmg-db`. Los comandos de configuración son deliberadamente opt-in:

```bash
mkdir -p "$CODEX_HOME"
cp docs/agent-workflows/profiles/zmg-etl.config.toml "$CODEX_HOME/"
cp docs/agent-workflows/profiles/zmg-db.config.toml "$CODEX_HOME/"
cp docs/agent-workflows/profiles/zmg-qa.config.toml "$CODEX_HOME/"
```

## Secuencia de colaboración

1. El Lead asigna `CONTRACT-001-ETL`: proponer campos, identidad, fixture y reglas de rechazo.
2. El Lead asigna `CONTRACT-001-DB`: revisar la propuesta y recomendar tablas/constraints compatibles, sin editar migraciones.
3. El Lead asigna `CONTRACT-001-QA`: revisar ambas propuestas y enumerar casos límite, sin cambiar producción.
4. El Lead compara los tres reportes y marca conflictos: por ejemplo, `geometry` como punto representativo versus preservación de geometría no puntual.
5. El Lead pide una reconciliación explícita y actualiza `docs/project-spec.md`, el diccionario y un ADR si la decisión es importante.
6. El Lead registra la decisión reconciliada: `source_id` canónico, `geometry_method`, estados de validación, `tags={}` y UUID de ejecución.
7. Solo tras aceptar el contrato se asignan tareas de implementación.

## Qué observar

Verifica que cada agente informe archivos (idealmente ninguno en esta revisión), decisiones, comandos, resultados, riesgos y preguntas abiertas. Una recomendación que agregue un timestamp de modificación de fuente o una municipalidad sin evidencia debe marcarse como incompatible.

## Verificación de delegación

En esta instalación, la delegación interactiva del harness se verifica cuando el Lead crea tres subagentes con tareas independientes, espera sus resultados y conserva sus reportes para reconciliación. El CLI `codex agents` permite explorar sesiones, pero no crear perfiles de rol; por eso no debe presentarse como mecanismo de creación de especialistas.
