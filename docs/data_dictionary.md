# Diccionario inicial de datos

| Campo normalizado | Tipo esperado | Requerido | Semántica |
|---|---|---:|---|
| `source` | string | sí | `openstreetmap` o `inegi_denue` |
| `object_type` | enum | sí | `node`, `way`, `relation` (OpenStreetMap) o `economic_unit` (INEGI DENUE) |
| `object_id` | integer positivo | sí | identificador OSM o `Id` de DENUE |
| `source_id` | string | sí | `source:object_type:object_id`, por ejemplo `openstreetmap:node:1001` |
| `name` | string/null | no | `tags.name`, sin fabricar valores |
| `category` | string | sí | categoría consultada: `cafe` |
| `establishment_kind` | enum | sí | `cafe`/`neveria`/`refresqueria`/`otro`; heurística sobre el nombre (ver `classify.py`), NO es un atributo oficial de ninguna fuente |
| `municipio` | string/null | no | solo INEGI DENUE: municipio de la consulta que trajo el registro (nunca inferido de texto libre); siempre `None` para OpenStreetMap |
| `ubicacion`, `areageo`, `clee` | string/null | no | campos oficiales crudos de INEGI DENUE (`Ubicacion`, `AreaGeo`, `CLEE`), copiados verbatim; siempre `None` para OpenStreetMap |
| `estrato`, `tipo`, `tipo_vialidad`, `calle`, `num_exterior`, `colonia`, `cp`, `telefono`, `sitio_internet`, `correo_e` | string/null | no | campos oficiales crudos de INEGI DENUE (`Estrato`, `Tipo`, `Tipo_vialidad`, `Calle`, `Num_Exterior`, `Colonia`, `CP`, `Telefono`, `Sitio_internet`, `Correo_e`), copiados verbatim; siempre `None` para OpenStreetMap |
| `latitude` | decimal/null | sí para aceptados | WGS84, rango -90..90 |
| `longitude` | decimal/null | sí para aceptados | WGS84, rango -180..180 |
| `geometry` | Point/null | sí para aceptados | punto representativo en SRID 4326 |
| `geometry_method` | enum/null | sí para aceptados | `node_coordinates`, `overpass_center` (OpenStreetMap) o `denue_coordinates` (INEGI DENUE) |
| `tags` | object | sí | atributos originales; `{}` si faltan |
| `source_updated_at` | timestamp/null | no | INEGI DENUE: `Fecha_Alta` (`"YYYY-MM"`) parseada a UTC, primer día del mes; `None` si falta o es inválida. OpenStreetMap: siempre `None` |
| `retrieved_at` | timestamp | sí | momento de adquisición |
| `run_id` | UUID string | sí | ejecución que produjo el registro |
| `validation_status` | enum | sí | `accepted`, `accepted_with_warning` o `rejected` |
| `rejection_reason` | enum/null | sí para rechazados | código estructurado; nulo para aceptados |

Un registro sin nombre puede ser válido con `accepted_with_warning`. Un registro sin identidad o coordenadas válidas no puede entrar a la capa analítica inicial. `outside_study_area` es un rechazo de alcance, no una coordenada malformada. El snapshot raw conserva también objetos rechazados.

La deduplicación conserva el primer elemento recibido para cada `source_id` y rechaza los posteriores con `duplicate_source_identity`; por eso el resultado es determinista para un mismo payload ordenado.

Razones iniciales: `malformed_response`, `missing_object_type`, `missing_object_id`, `invalid_object_id`, `missing_coordinates`, `invalid_latitude`, `invalid_longitude`, `missing_way_or_relation_center`, `unsupported_geometry`, `outside_study_area` y `duplicate_source_identity`.

`analytics.establecimientos` contiene exactamente los `source_id` aceptados en la última corrida cargada de su `source`: un `source_id` ausente o rechazado en la corrida actual se retira físicamente (ADR-006, issue #49), aunque haya estado aceptado en una corrida anterior. `run_id` en `analytics.establecimientos` es siempre el de la última corrida cargada para esa fuente, nunca el de la primera vez que se vio el registro. El historial de qué valores tenía un registro retirado vive en `staging.cafe_records`, que es append-only por corrida y nunca se poda.
