"""MongoDB connection management.

Replaces the asyncpg engine. The control plane lives in one database;
each institution gets its own database (`<root>_t_<slug>`), which keeps
the structural isolation the schema-per-tenant design guaranteed: there is
no code path that can name another institution's database, because the
slug arrives only from the verified token.
"""
from __future__ import annotations

import threading

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None
_lock = threading.Lock()


def client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _client = AsyncIOMotorClient(
                    settings.database_url,
                    serverSelectionTimeoutMS=15000,
                )
    return _client


async def ping() -> bool:
    """True when the server answers. Used by startup and health reporting."""
    try:
        await client().admin.command("ping")
        return True
    except Exception:  # noqa: BLE001 - callers report the failure themselves
        return False


def root_db_name() -> str:
    """Database named in the URI (or the configured fallback)."""
    return settings.mongo_root_db


def platform_db() -> AsyncIOMotorDatabase:
    return client()[root_db_name()]


def tenant_db_name(slug: str) -> str:
    if not slug:
        raise ValueError("tenant slug is required — there is no default tenant")
    return f"{root_db_name()}{settings.tenant_db_suffix}{slug}"


def tenant_db(slug: str) -> AsyncIOMotorDatabase:
    return client()[tenant_db_name(slug)]


async def dispose() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def tenant_slugs() -> list[str]:
    """Institutions that already exist, by database-name prefix."""
    names = await client().list_database_names()
    prefix = f"{root_db_name()}{settings.tenant_db_suffix}"
    return sorted(n[len(prefix):] for n in names if n.startswith(prefix))
