"""Shared safety guard for integration tests that truncate a real database.

Issue #59: a session pointed ZMG_TEST_DATABASE_URL at the development
database (name "zmg_cafes", the POSTGRES_DB default in .env.example/
compose.yaml) and lost real loaded data to the TRUNCATE fixtures below.
"""

import psycopg

_DEV_DATABASE_NAME = "zmg_cafes"


def truncate_project_tables(database_url: str) -> None:
    """Truncate the project's four pipeline schemas, refusing the dev database."""

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            (name,) = cursor.fetchone()
            # shortcut: blocks only the literal default dev db name "zmg_cafes";
            # rename-aware detection would need more, revisit if that default changes.
            if name == _DEV_DATABASE_NAME:
                raise RuntimeError(
                    f"Refusing to truncate database {name!r}: ZMG_TEST_DATABASE_URL "
                    "must point at a disposable database, never at the development "
                    "database (see docs/database.md)."
                )
            cursor.execute(
                "TRUNCATE analytics.establecimientos, staging.cafe_records,"
                " raw.overpass_snapshots, raw.denue_snapshots, meta.pipeline_runs"
            )
