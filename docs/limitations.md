# Limitaciones conocidas

- El área inicial es un bounding box provisional.
- OpenStreetMap es comunitario y puede contener datos faltantes, duplicados reales o información desactualizada.
- La identidad de objeto no equivale a identidad de negocio; la resolución de entidades queda fuera del primer MVP.
- Los objetos lineales o poligonales requieren una política de punto representativo y validación; el fixture incluye un `way` con `center` para probar esa diferencia.
- No se han elegido límites municipales, por lo que el filtro municipal no está implementado.
- No se hacen llamadas live durante este milestone.
