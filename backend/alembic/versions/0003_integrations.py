"""integrations and document-integration links

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ts = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "integrations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "increment_id",
            sa.Integer,
            sa.ForeignKey("architecture_increments.id"),
            nullable=False,
        ),
        sa.Column("integration_id", sa.String(120), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column(
            "source_application", sa.String(200), nullable=False, server_default=""
        ),
        sa.Column(
            "target_application", sa.String(200), nullable=False, server_default=""
        ),
        sa.Column(
            "required", sa.Boolean, nullable=False, server_default=sa.true()
        ),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column(
            "document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=True
        ),
        sa.Column("metadata_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column(
            "contract_filename", sa.String(200), nullable=False, server_default=""
        ),
        sa.Column("contract_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("contract_content", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("increment_id", "integration_id"),
    )
    op.create_index(
        "ix_integrations_integration_id", "integrations", ["integration_id"]
    )

    op.create_table(
        "document_integration_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer,
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column(
            "integration_id",
            sa.Integer,
            sa.ForeignKey("integrations.id"),
            nullable=False,
        ),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "integration_id"),
    )


def downgrade() -> None:
    op.drop_table("document_integration_links")
    op.drop_index("ix_integrations_integration_id", table_name="integrations")
    op.drop_table("integrations")
