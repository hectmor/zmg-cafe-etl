# Base de datos y migraciones

La base local usa PostgreSQL 17 con PostGIS y Flyway. Las migraciones versionadas están en `db/migrations`; Flyway registra su historial en el schema `meta`.

## Inicio local

```bash
docker compose up -d db
docker compose --profile migrate run --rm flyway
```

Para consultar el estado de las migraciones:

```bash
docker compose --profile migrate run --rm flyway info
```

La migración inicial crea los schemas `meta`, `raw`, `staging` y `analytics`, junto con geometrías `Point` en SRID 4326 e índices GiST. El loader todavía no escribe en estas tablas; esa integración corresponde a M4.

Las credenciales de desarrollo están en `.env.example`. Crea un archivo `.env` local para usar valores distintos. Si el puerto 5432 ya está ocupado, define otro `POSTGRES_PORT` y ajusta `DATABASE_URL` al mismo puerto.

Para detener el servicio sin borrar la base local, ejecuta `docker compose stop db`. No uses `docker compose down -v` para una pausa normal: `-v` elimina el volumen persistente.
