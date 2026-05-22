"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ts = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("git_path", sa.String(500), nullable=False),
        sa.Column("default_branch", sa.String(80), nullable=False, server_default="main"),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_repositories_slug", "repositories", ["slug"])

    op.create_table(
        "application_groups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("repository_id", sa.Integer, sa.ForeignKey("repositories.id"), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("repository_id", "slug"),
    )
    op.create_index("ix_application_groups_slug", "application_groups", ["slug"])

    op.create_table(
        "architecture_increments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("application_group_id", sa.Integer, sa.ForeignKey("application_groups.id"), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="draft"),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("application_group_id", "slug"),
    )
    op.create_index("ix_architecture_increments_slug", "architecture_increments", ["slug"])

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("increment_id", sa.Integer, sa.ForeignKey("architecture_increments.id"), nullable=False),
        sa.Column("type", sa.String(40), nullable=False, server_default="hld"),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("git_branch", sa.String(80), nullable=False, server_default="main"),
        sa.Column("head_commit", sa.String(64), nullable=True),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "document_sections",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("document_sections.id"), nullable=True),
        sa.Column("order_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("number", sa.String(20), nullable=False, server_default=""),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text, nullable=False, server_default=""),
        sa.Column("kind", sa.String(40), nullable=False, server_default="custom"),
        sa.Column("git_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "diagrams",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("section_id", sa.Integer, sa.ForeignKey("document_sections.id"), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("source", sa.Text, nullable=False, server_default=""),
        sa.Column("mmd_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("svg_path", sa.String(500), nullable=False, server_default=""),
        sa.Column("svg", sa.Text, nullable=False, server_default=""),
        sa.Column("render_status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("last_error", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", _ts, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("artifact_path", sa.String(500), nullable=True),
        sa.Column("error", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "validation_results",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("section_id", sa.Integer, sa.ForeignKey("document_sections.id"), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in (
        "validation_results",
        "export_jobs",
        "diagrams",
        "document_sections",
        "documents",
        "architecture_increments",
        "application_groups",
        "repositories",
    ):
        op.drop_table(table)
