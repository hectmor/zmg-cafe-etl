# Fuente inicial: OpenStreetMap y Overpass

OpenStreetMap es la base de datos colaborativa; Overpass API es un servicio de consulta para extraer subconjuntos. No son la misma cosa. La consulta inicial usa `amenity=cafe` y `nwr` para considerar nodos, vías y relaciones. Con `out center tags`, los objetos no puntuales pueden traer un punto representativo de servicio.

## Contrato de extracción

La respuesta esperada es un objeto JSON con `elements`, donde cada elemento tiene `type`, `id` y, según el tipo, `lat`/`lon` o `center.lat`/`center.lon`. `tags` es opcional. El extractor debe rechazar una respuesta sin `elements` o con tipos incompatibles; no debe transformar silenciosamente HTML de un error HTTP.

La respuesta almacenada debe conservarse antes de cualquier normalización. El nombre de archivo futuro será `data/raw/openstreetmap/YYYY/MM/DD/<run_id>.json`; nunca se sobrescribe una ejecución anterior.

## Geografía

El bounding box en `config/sources.yaml` es una aproximación operativa para desarrollo, no una frontera oficial de la ZMG. Los límites municipales están pendientes de una fuente autoritativa, licencia reutilizable, CRS y definición geográfica documentados. No se asignarán municipios con umbrales inventados ni con texto de direcciones.

## Atribución y limitaciones

La atribución prevista es “© OpenStreetMap contributors” y la licencia es ODbL. Deben revisarse las obligaciones aplicables antes de publicar una base derivada. Los resultados reflejan únicamente objetos disponibles en la fuente: no son un censo, no garantizan que un café opere actualmente y no cubren necesariamente todos los negocios.

## Campos iniciales

| Campo fuente | Uso | Ausencia |
|---|---|---|
| `type`, `id` | identidad estable | rechazo si falta |
| `lat`, `lon` | geometría de node | usar `center` para way/relation |
| `center.lat`, `center.lon` | punto representativo pedido a Overpass | rechazo si no hay política válida |
| `tags.name` | nombre opcional | conservar como nulo |
| `tags` | trazabilidad | objeto vacío |
