# Limitaciones conocidas

- El área inicial es un bounding box provisional.
- OpenStreetMap es comunitario y puede contener datos faltantes, duplicados reales o información desactualizada.
- La identidad de objeto no equivale a identidad de negocio; la resolución de entidades queda fuera del primer MVP.
- Los objetos lineales o poligonales requieren una política de punto representativo y validación; el fixture incluye un `way` con `center` para probar esa diferencia.
- No se han elegido límites municipales, por lo que el filtro municipal no está implementado.
- No se hacen llamadas live durante este milestone.
- `analytics.establecimientos` no conserva historial propio: un registro retirado (ADR-006) solo es reconstruible consultando `staging.cafe_records`, no desde la capa analítica misma.
- Una respuesta **parcial** de Overpass (elementos faltantes con el campo `remark` presente, sin estar vacía) no se detecta hoy y podría retirar cafés por error; solo la respuesta completamente vacía está protegida (issue #49). Candidata a un issue de ETL aparte que revise `remark`.
- Si en el futuro se poda `staging.cafe_records`, se pierde la auditoría de qué registros se retiraron y cuándo.
