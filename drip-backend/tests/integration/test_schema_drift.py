"""Compare every migrated table against ORM metadata, not just readable columns."""

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.models.base import Base

pytestmark = pytest.mark.integration


async def test_full_migrated_schema_matches_models(test_engine):
    async with test_engine.begin() as connection:

        def supplemental(sync_connection):
            inspector = inspect(sync_connection)
            checks = {
                table.name: sorted(
                    (item["name"], item["sqltext"])
                    for item in inspector.get_check_constraints(table.name)
                )
                for table in Base.metadata.sorted_tables
            }
            enums = {item["name"]: item["labels"] for item in inspector.get_enums()}
            primary_keys = {
                table.name: inspector.get_pk_constraint(table.name)["constrained_columns"]
                for table in Base.metadata.sorted_tables
            }
            return checks, enums, primary_keys

        expected_checks, expected_enums, expected_keys = await connection.run_sync(supplemental)
        await connection.run_sync(Base.metadata.drop_all)

        def compare(sync_connection):
            config = Config("alembic.ini")
            config.attributes["connection"] = sync_connection
            command.upgrade(config, "head")
            context = MigrationContext.configure(
                sync_connection,
                opts={
                    "compare_type": True,
                    "compare_server_default": True,
                },
            )
            return compare_metadata(context, Base.metadata)

        differences = await connection.run_sync(compare)
        actual_checks, actual_enums, actual_keys = await connection.run_sync(supplemental)

        def brief(item):
            if isinstance(item, list):
                return "; ".join(brief(child) for child in item)
            if item[0].startswith("modify_"):
                return f"{item[0]} {item[2]}.{item[3]}: {item[-2]} -> {item[-1]}"
            obj = item[-1]
            return f"{item[0]} {getattr(obj, 'table', '')}.{getattr(obj, 'name', '')}: {obj}"

        assert differences == [], "\n".join(brief(item) for item in differences)
        assert actual_checks == expected_checks
        assert actual_enums == expected_enums
        assert actual_keys == expected_keys
