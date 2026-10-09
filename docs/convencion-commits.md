# Convención de commits

## Commits

- Usar siempre la identidad del usuario `hectmor`.
- La identidad Git asociada actualmente es `Hector Moreno <h.morenocarrion@gmail.com>`.
- Nunca agregar `Co-Authored-By` de Claude ni de otro agente al mensaje del commit.
- Cada commit debe contener únicamente una línea de encabezado.
- No agregar cuerpo, descripción adicional ni trailers después del encabezado.
- Escribir los mensajes de commit en inglés.
- No incluir secretos, credenciales, archivos `.env`, snapshots raw productivos grandes ni artefactos generados.

## Formato obligatorio

```text
type(scope): message
```

Ejemplos válidos:

```text
feat(extract): add Overpass snapshot preservation
fix(validate): reject impossible longitude values
docs(workflow): document specialist agent roles
test(transform): cover duplicate source identities
chore(deps): add requirements file
```

## Tipos permitidos

- `feat`: nueva funcionalidad.
- `fix`: corrección de errores.
- `docs`: cambios de documentación.
- `test`: cambios de pruebas.
- `refactor`: reestructuración sin cambio funcional.
- `perf`: mejora de rendimiento.
- `build`: dependencias o configuración de construcción.
- `ci`: integración continua.
- `chore`: mantenimiento general.
- `revert`: reversión de un commit.

## Reglas del encabezado

- Usar el tiempo presente y forma imperativa: `add`, `fix`, `update`, `remove`.
- Escribir el mensaje en minúsculas después de `:`.
- No terminar el mensaje con punto.
- Mantenerlo idealmente por debajo de 72 caracteres.
- Describir un único cambio lógico.
- Para cambios incompatibles, agregar `!` al header, sin añadir cuerpo:

```text
feat(api)!: change GeoJSON response contract
```

## Validación antes del commit

```bash
git diff --check
pytest
ruff check .
ruff format --check .
```

El commit debe contener solo los archivos relacionados con la tarea y debe poder revisarse de forma independiente.
