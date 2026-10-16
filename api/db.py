"""Read-only access to the analytics layer."""

from __future__ import annotations

from typing import Any

import psycopg


class StoreError(RuntimeError):
    """Raised when the analytics layer cannot answer a query."""


def normalize_dsn(dsn: str) -> str:
    """Return a DSN psycopg can open, dropping SQLAlchemy driver suffixes."""

    for prefix in ("postgresql+psycopg://", "postgres+psycopg://"):
        if dsn.startswith(prefix):
            return f"postgresql://{dsn[len(prefix) :]}"
    return dsn


class AnalyticsStore:
    """Query the consumer-facing `analytics` schema of the café database."""

    def __init__(self, dsn: str) -> None:
        self._dsn = normalize_dsn(dsn)

    def ping(self) -> bool:
        """Return True when the database answers a trivial query."""

        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
        except psycopg.Error:
            return False
        return True

    def count_cafes(self) -> int:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT count(*) FROM analytics.establecimientos")
                    row = cursor.fetchone()
                    return int(row[0]) if row else 0
        except psycopg.Error as error:
            raise StoreError(f"Could not count cafes: {error}") from error

    def list_cafes(self, *, limit: int, offset: int) -> list[dict[str, Any]]:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT source_id, source, object_type, object_id, name, category,"
                        " establishment_kind, municipio, ubicacion, areageo, clee,"
                        " estrato, tipo, tipo_vialidad, calle, num_exterior, colonia, cp,"
                        " telefono, sitio_internet, correo_e,"
                        " latitude, longitude, geometry_method, tags, source_updated_at,"
                        " retrieved_at, run_id"
                        " FROM analytics.establecimientos"
                        " ORDER BY source_id"
                        " LIMIT %(limit)s OFFSET %(offset)s",
                        {"limit": limit, "offset": offset},
                    )
                    return [dict(zip(CAFE_COLUMNS, row)) for row in cursor.fetchall()]
        except psycopg.Error as error:
            raise StoreError(f"Could not list cafes: {error}") from error

    def get_cafe(self, source_id: str) -> dict[str, Any] | None:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT source_id, source, object_type, object_id, name, category,"
                        " establishment_kind, municipio, ubicacion, areageo, clee,"
                        " estrato, tipo, tipo_vialidad, calle, num_exterior, colonia, cp,"
                        " telefono, sitio_internet, correo_e,"
                        " latitude, longitude, geometry_method, tags, source_updated_at,"
                        " retrieved_at, run_id"
                        " FROM analytics.establecimientos"
                        " WHERE source_id = %(source_id)s",
                        {"source_id": source_id},
                    )
                    row = cursor.fetchone()
                    return dict(zip(CAFE_COLUMNS, row)) if row else None
        except psycopg.Error as error:
            raise StoreError(f"Could not read cafe {source_id}: {error}") from error

    def stats(self) -> dict[str, Any]:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT count(*),"
                        " count(*) FILTER (WHERE name IS NOT NULL),"
                        " count(*) FILTER (WHERE name IS NULL)"
                        " FROM analytics.establecimientos"
                    )
                    total, with_name, without_name = cursor.fetchone()
                    cursor.execute(
                        "SELECT object_type, count(*) FROM analytics.establecimientos"
                        " GROUP BY object_type ORDER BY object_type"
                    )
                    by_object_type = dict(cursor.fetchall())
                    cursor.execute(
                        "SELECT geometry_method, count(*) FROM analytics.establecimientos"
                        " GROUP BY geometry_method ORDER BY geometry_method"
                    )
                    by_geometry_method = dict(cursor.fetchall())
                    cursor.execute(
                        "SELECT source, count(*) FROM analytics.establecimientos"
                        " GROUP BY source ORDER BY source"
                    )
                    by_source = dict(cursor.fetchall())
        except psycopg.Error as error:
            raise StoreError(f"Could not compute stats: {error}") from error
        return {
            "total": int(total),
            "with_name": int(with_name),
            "without_name": int(without_name),
            "by_object_type": {str(key): int(value) for key, value in by_object_type.items()},
            "by_geometry_method": {
                str(key): int(value) for key, value in by_geometry_method.items()
            },
            "by_source": {str(key): int(value) for key, value in by_source.items()},
        }

    def list_runs(self, *, limit: int) -> list[dict[str, Any]]:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT run_id, source, status, started_at, completed_at"
                        " FROM meta.pipeline_runs"
                        " ORDER BY started_at DESC"
                        " LIMIT %(limit)s",
                        {"limit": limit},
                    )
                    return [dict(zip(RUN_COLUMNS, row)) for row in cursor.fetchall()]
        except psycopg.Error as error:
            raise StoreError(f"Could not list pipeline runs: {error}") from error

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._dsn)


RUN_COLUMNS = (
    "run_id",
    "source",
    "status",
    "started_at",
    "completed_at",
)

CAFE_COLUMNS = (
    "source_id",
    "source",
    "object_type",
    "object_id",
    "name",
    "category",
    "establishment_kind",
    "municipio",
    "ubicacion",
    "areageo",
    "clee",
    "estrato",
    "tipo",
    "tipo_vialidad",
    "calle",
    "num_exterior",
    "colonia",
    "cp",
    "telefono",
    "sitio_internet",
    "correo_e",
    "latitude",
    "longitude",
    "geometry_method",
    "tags",
    "source_updated_at",
    "retrieved_at",
    "run_id",
)
