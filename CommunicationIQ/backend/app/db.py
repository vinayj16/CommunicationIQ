"""MongoDB data layer — Beanie ODM over Motor, database-per-tenant.

Two kinds of documents:

* Control-plane documents (``app.models.platform``) live in one database,
  ``CommunicationIQ`` (taken from the URI). Registered once at startup.
* Per-institution documents (``app.models.tenant``) live in a database named
  ``tenant_<slug>`` each. There is no shared tenant database; the database name
  *is* the isolation boundary (TEN-12). Because the set of institutions is open,
  the tenant documents are bound to their database lazily, the first time a
  tenant is touched, by ``ensure_tenant_models``.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from urllib.parse import urlparse

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from beanie import init_beanie

from app.config import settings
from app.models.platform import CONTROL_DOCUMENTS
from app.models.tenant import TENANT_DOCUMENTS


client = AsyncIOMotorClient(settings.mongo_uri, uuidRepresentation="standard")

CONTROL_DB_NAME = settings.control_db_name


def control_db() -> AsyncIOMotorDatabase:
    """The control-plane database (``CommunicationIQ``)."""
    return client[CONTROL_DB_NAME]


def tenant_db_name(slug: str) -> str:
    return f"{settings.tenant_schema_prefix}{slug}"


def tenant_db(slug: str) -> AsyncIOMotorDatabase:
    """The isolated database for one institution."""
    return client[tenant_db_name(slug)]


_client_inited = False


async def init_mongo() -> None:
    """Ping and register the control-plane documents. Idempotent.

    Raising here is tolerated by the caller (startup keeps serving), but the
    control models will be unusable until a connection is available.
    """
    global _client_inited
    if _client_inited:
        return
    await client.admin.command("ping")
    await init_beanie(database=control_db(), document_models=CONTROL_DOCUMENTS)
    _client_inited = True


_tenant_bundles: dict[str, SimpleNamespace] = {}
_tenant_locks: dict[str, asyncio.Lock] = {}


async def ensure_tenant_models(slug: str) -> SimpleNamespace:
    """Return a namespace of Beanie Document classes bound to ``tenant_<slug>``.

    The bundle is created and its documents registered with Beanie on first
    use, then cached. Each tenant gets distinct document classes, so a query on
    one institution can never touch another's database.
    """
    cached = _tenant_bundles.get(slug)
    if cached is not None:
        return cached
    lock = _tenant_locks.setdefault(slug, asyncio.Lock())
    async with lock:
        cached = _tenant_bundles.get(slug)
        if cached is not None:
            return cached
        db = tenant_db(slug)
        classes = {
            base.__name__: type(base.__name__, (base,), {})
            for base in TENANT_DOCUMENTS
        }
        await init_beanie(database=db, document_models=list(classes.values()))
        bundle = SimpleNamespace(**classes)
        _tenant_bundles[slug] = bundle
        return bundle


def get_tenant_models(slug: str) -> SimpleNamespace:
    """Synchronous accessor — only valid after ``ensure_tenant_models`` ran."""
    return _tenant_bundles[slug]
