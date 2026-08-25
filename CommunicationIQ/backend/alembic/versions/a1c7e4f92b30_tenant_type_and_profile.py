"""tenant type and profile

Adds the two columns the Tenant model gained after the baseline: what kind of
customer a tenant is, and the paperwork about them (address, contacts,
courses).

Written because their absence broke a real deployment. The columns were added
to the model and to a runtime "add any missing columns" helper that runs
inside the API's startup — but the start command seeds the database *before*
the API starts, so the seeder inserted a `tenant_type` into a table that did
not have one and the process exited. Alembic owns the control-plane schema;
adding a column to the model without a revision here is the bug, and the
runtime helper only ever hid it on machines that were already migrated.

Both columns are NOT NULL with a server default, so this applies cleanly to a
database that already has rows.

Revision ID: a1c7e4f92b30
Revises: 5d214539fbc4
Create Date: 2026-08-18 15:20:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "a1c7e4f92b30"
down_revision: str | None = "5d214539fbc4"
branch_labels = None
depends_on = None


def _has(column: str) -> bool:
    """Is the column already there?

    It can be, on any database that ran the API before this revision existed:
    the old runtime helper added these same columns at startup. Checking makes
    the revision safe on both a fresh database and one that was patched behind
    Alembic's back.
    """
    inspector = sa.inspect(op.get_bind())
    return column in {c["name"] for c in inspector.get_columns("tenants")}


def upgrade() -> None:
    if _has("tenant_type") and _has("profile"):
        return
    if not _has("tenant_type"):
        _add_tenant_type()
    if not _has("profile"):
        _add_profile()


def _add_tenant_type() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "tenant_type",
            sa.String(length=40),
            nullable=False,
            server_default="engineering_college",
        ),
    )
    op.create_index("ix_tenants_tenant_type", "tenants", ["tenant_type"])


def _add_profile() -> None:
    op.add_column(
        "tenants",
        sa.Column("profile", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("tenants", "profile")
    op.drop_index("ix_tenants_tenant_type", table_name="tenants")
    op.drop_column("tenants", "tenant_type")
