# Diccionario inicial de datos

| Campo normalizado | Tipo esperado | Requerido | Semántica |
|---|---|---:|---|
| `source` | string | sí | `openstreetmap` |
| `object_type` | enum | sí | `node`, `way` o `relation` |
| `object_id` | integer positivo | sí | identificador OSM |
| `source_id` | string | sí | `source:object_type:object_id`, por ejemplo `openstreetmap:node:1001` |
| `name` | string/null | no | `tags.name`, sin fabricar valores |
| `category` | string | sí | categoría consultada: `cafe` |
| `latitude` | decimal/null | sí para aceptados | WGS84, rango -90..90 |
| `longitude` | decimal/null | sí para aceptados | WGS84, rango -180..180 |
| `geometry` | Point/null | sí para aceptados | punto representativo en SRID 4326 |
| `geometry_method` | enum/null | sí para aceptados | `node_coordinates` o `overpass_center` |
| `tags` | object | sí | atributos originales; `{}` si faltan |
| `source_updated_at` | timestamp/null | no | solo si la fuente lo proporciona |
| `retrieved_at` | timestamp | sí | momento de adquisición |
| `run_id` | UUID string | sí | ejecución que produjo el registro |
| `validation_status` | enum | sí | `accepted`, `accepted_with_warning` o `rejected` |
| `rejection_reason` | enum/null | sí para rechazados | código estructurado; nulo para aceptados |

Un registro sin nombre puede ser válido con `accepted_with_warning`. Un registro sin identidad o coordenadas válidas no puede entrar a la capa analítica inicial. `outside_study_area` es un rechazo de alcance, no una coordenada malformada. El snapshot raw conserva también objetos rechazados.

La deduplicación conserva el primer elemento recibido para cada `source_id` y rechaza los posteriores con `duplicate_source_identity`; por eso el resultado es determinista para un mismo payload ordenado.

Razones iniciales: `malformed_response`, `missing_object_type`, `missing_object_id`, `invalid_object_id`, `missing_coordinates`, `invalid_latitude`, `invalid_longitude`, `missing_way_or_relation_center`, `unsupported_geometry`, `outside_study_area` y `duplicate_source_identity`.
