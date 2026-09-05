"""Compare normalized PostgreSQL schemas for a fresh baseline and an upgraded database."""

import argparse
import asyncio
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine


def _sorted(items: Sequence[dict]) -> list[dict]:
    return sorted(items, key=lambda item: json.dumps(item, sort_keys=True, default=str))


def _normalize_check(sqltext: object) -> str:
    """Normalize equivalent PostgreSQL renderings produced by create/alter paths."""
    normalized = " ".join(str(sqltext).split())
    normalized = re.sub(r"::character varying(?:::text)?", "::text", normalized)
    normalized = normalized.replace("]::text[]", "]")
    return normalized


def _snapshot(sync_connection) -> dict:
    inspector = inspect(sync_connection)
    tables: dict[str, dict] = {}
    for table_name in sorted(
        name for name in inspector.get_table_names() if name != "alembic_version"
    ):
        columns = [
            {
                "name": column["name"],
                "type": str(column["type"]),
                "nullable": column["nullable"],
                "default": str(column.get("default")),
            }
            for column in inspector.get_columns(table_name)
        ]
        foreign_keys = [
            {
                "columns": item["constrained_columns"],
                "target_table": item["referred_table"],
                "target_columns": item["referred_columns"],
                "options": item.get("options", {}),
            }
            for item in inspector.get_foreign_keys(table_name)
        ]
        uniques = [
            {"columns": item["column_names"]}
            for item in inspector.get_unique_constraints(table_name)
        ]
        checks = [
            {"sqltext": _normalize_check(item["sqltext"])}
            for item in inspector.get_check_constraints(table_name)
        ]
        indexes = [
            {"columns": item["column_names"], "unique": item["unique"]}
            for item in inspector.get_indexes(table_name)
            if not item.get("duplicates_constraint")
        ]
        tables[table_name] = {
            "columns": _sorted(columns),
            "primary_key": inspector.get_pk_constraint(table_name)["constrained_columns"],
            "foreign_keys": _sorted(foreign_keys),
            "unique_constraints": _sorted(uniques),
            "check_constraints": _sorted(checks),
            "indexes": _sorted(indexes),
        }
    return {"tables": tables}


async def snapshot(database_url: str) -> dict:
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        result = await connection.run_sync(_snapshot)
        enum_rows = (
            await connection.execute(
                text(
                    """
                    SELECT type_name.typname, enum_value.enumlabel
                    FROM pg_type AS type_name
                    JOIN pg_enum AS enum_value ON enum_value.enumtypid = type_name.oid
                    JOIN pg_namespace AS namespace ON namespace.oid = type_name.typnamespace
                    WHERE namespace.nspname = 'public'
                    ORDER BY type_name.typname, enum_value.enumsortorder
                    """
                )
            )
        ).all()
        enums: dict[str, list[str]] = {}
        for enum_name, enum_value in enum_rows:
            enums.setdefault(enum_name, []).append(enum_value)
        result["enums"] = enums
    await engine.dispose()
    return result


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fresh_database_url")
    parser.add_argument("upgraded_database_url")
    arguments = parser.parse_args()
    fresh, upgraded = await asyncio.gather(
        snapshot(arguments.fresh_database_url),
        snapshot(arguments.upgraded_database_url),
    )
    if fresh != upgraded:
        print("Schema equivalence: FAIL")
        fresh_tables = fresh["tables"]
        upgraded_tables = upgraded["tables"]
        for table_name in sorted(set(fresh_tables) | set(upgraded_tables)):
            if fresh_tables.get(table_name) == upgraded_tables.get(table_name):
                continue
            if table_name not in fresh_tables or table_name not in upgraded_tables:
                print(f"table={table_name} presence differs")
                continue
            for key in fresh_tables[table_name]:
                if fresh_tables[table_name][key] != upgraded_tables[table_name][key]:
                    print(f"table={table_name} aspect={key}")
                    print(
                        json.dumps(
                            {
                                "fresh": fresh_tables[table_name][key],
                                "upgraded": upgraded_tables[table_name][key],
                            },
                            default=str,
                        )
                    )
        if fresh.get("enums") != upgraded.get("enums"):
            print("enum values differ")
            print(json.dumps({"fresh": fresh.get("enums"), "upgraded": upgraded.get("enums")}))
        return 1
    print("Schema equivalence: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
