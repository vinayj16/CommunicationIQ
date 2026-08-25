"""Alembic environment.

Migrations here own the **control plane** (``public``) only. Institution
schemas are not migrated by revision files: they are created from
``TenantBase.metadata`` by ``app.provisioning``, once per institution, so a new
tenant provisioned today and one provisioned a year ago cannot drift apart.
When a tenant table changes, the migration applies the same DDL across every
``tenant_%`` schema in one revision — see the helper below.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.db import PlatformBase
from app.models import platform, tenant  # noqa: F401 — registers metadata

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = PlatformBase.metadata


def tenant_schemas(connection: Connection) -> list[str]:
    """Every provisioned institution schema.

    Migrations that touch tenant tables iterate this list rather than naming
    schemas, so nothing is missed when a new institution exists.
    """
    rows = connection.execute(text(
        "SELECT schema_name FROM information_schema.schemata "
        "WHERE schema_name LIKE :prefix ORDER BY schema_name"
    ), {"prefix": f"{settings.tenant_schema_prefix}%"})
    return [r[0] for r in rows]


def _include(obj, name, type_, reflected, compare_to) -> bool:
    """Keep autogenerate focused on ``public``.

    Without this, the tenant tables (declared against the ``tenant``
    placeholder) would be compared against every real tenant schema and
    produce noise on every revision.
    """
    if type_ == "table" and obj.schema not in (None, "public"):
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=False,
        include_object=_include,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=False,
        include_object=_include,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
