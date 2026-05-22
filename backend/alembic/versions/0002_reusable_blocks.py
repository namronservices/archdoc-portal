"""reusable blocks and document reuse instances

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ts = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "reusable_blocks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("block_id", sa.String(200), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("category", sa.String(80), nullable=False, server_default=""),
        sa.Column("version", sa.String(40), nullable=False, server_default=""),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("owner", sa.String(120), nullable=False, server_default=""),
        sa.Column("tags", sa.Text, nullable=False, server_default="[]"),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column("git_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("scope", sa.String(40), nullable=True),
        sa.Column("derived_from", sa.String(200), nullable=True),
        sa.Column("derived_from_version", sa.String(40), nullable=False, server_default=""),
        sa.Column("derivation_type", sa.String(40), nullable=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_reusable_blocks_block_id", "reusable_blocks", ["block_id"])

    op.create_table(
        "document_reuse_instances",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("section_id", sa.Integer, sa.ForeignKey("document_sections.id"), nullable=False),
        sa.Column("block_id", sa.String(200), nullable=False),
        sa.Column("reuse_mode", sa.String(20), nullable=False),
        sa.Column("source_version", sa.String(40), nullable=False, server_default=""),
        sa.Column("derived_block_id", sa.String(200), nullable=True),
        sa.Column("snapshot_content", sa.Text, nullable=False, server_default=""),
        sa.Column("rationale", sa.Text, nullable=False, server_default=""),
        sa.Column("status", sa.String(40), nullable=False, server_default="active"),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("document_reuse_instances")
    op.drop_table("reusable_blocks")
