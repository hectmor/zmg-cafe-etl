# Tutorial 01: entender la fuente

## Objetivos

Distinguir OpenStreetMap de Overpass API, reconocer objetos OSM y entender por qué una consulta no equivale a un censo.

## Qué problema resuelve

Antes de escribir ETL hay que definir qué se consulta, cómo se identifica un objeto y qué limitaciones tiene la cobertura.

## Archivos y comandos

La configuración está en `config/sources.yaml` y el fixture en `tests/fixtures/overpass_cafes_sample.json`. Valida el fixture con:

```bash
uv run pytest tests/unit/test_foundation.py
```

Un `node` trae `lat`/`lon`; un `way` o `relation` puede necesitar `center` o una política geométrica explícita. Un nombre ausente no invalida automáticamente un café.

## Ejercicio

Explica la diferencia entre `source_id` y una identidad de negocio real. Después identifica qué campos del fixture son opcionales.

## Siguiente etapa

El extractor recibirá la plantilla configurada y producirá un resultado con payload, metadatos y `run_id`, sin transformar todavía los registros.
