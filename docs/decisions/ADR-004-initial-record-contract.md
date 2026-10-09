# ADR-004: Contrato inicial de registro normalizado

- **Estado:** aceptado para implementación ETL; sujeto a evolución versionada.
- **Contexto:** las revisiones ETL, DB y QA encontraron ambigüedad en identidad, geometría y estados de calidad.
- **Decisión:** separar `object_type` y `object_id`; serializar `source_id` como `source:object_type:object_id`; representar analytics como `Point` SRID 4326; conservar la respuesta raw; usar `geometry_method`; tratar `tags` ausentes como `{}`; y usar `accepted`, `accepted_with_warning` y `rejected` en staging.
- **Consecuencias:** el modelo es auditable y compatible con PostGIS, pero no preserva la geometría OSM completa en analytics. Los objetos fuera del área y los rechazados permanecen inspeccionables sin contaminar la capa analítica. `run_id` será UUID serializado en Python y UUID en DB.
- **Alternativas descartadas:** usar solo `source_id` sin componentes; inventar centroides; interpretar `osm3s.timestamp_osm_base` como modificación por objeto; asignar municipios antes de contar con límites confiables.
