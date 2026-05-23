"""enterprise repository — TOGAF objects and HLD context links

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ts = sa.DateTime(timezone=True)


def upgrade() -> None:
    # --- ApplicationGroup: TOGAF columns + nullable repository_id ---------
    op.add_column(
        "application_groups",
        sa.Column("domain_slug", sa.String(120), nullable=True),
    )
    op.add_column(
        "application_groups",
        sa.Column("archimate_type", sa.String(80), nullable=True),
    )
    op.add_column(
        "application_groups",
        sa.Column("git_path", sa.String(500), nullable=True),
    )
    op.alter_column(
        "application_groups", "repository_id", existing_type=sa.Integer(), nullable=True
    )
    # Drop the old (repository_id, slug) uniqueness; slugs are enterprise-wide now.
    op.drop_constraint(
        "application_groups_repository_id_slug_key",
        "application_groups",
        type_="unique",
    )
    # Deduplicate any existing slug collisions before applying the global unique
    # constraint — older rows may share a slug across repositories.
    op.execute(
        """
        UPDATE application_groups AS ag
        SET slug = ag.slug || '-' || ag.id
        WHERE ag.id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY slug ORDER BY id) AS rn
                FROM application_groups
            ) sub
            WHERE sub.rn > 1
        )
        """
    )
    op.create_unique_constraint(
        "application_groups_slug_key", "application_groups", ["slug"]
    )

    # --- Enterprise tables ------------------------------------------------
    def _enterprise_columns(extra: list[sa.Column]) -> list[sa.Column]:
        return extra + [
            sa.Column("archimate_type", sa.String(80), nullable=True),
            sa.Column("git_path", sa.String(500), nullable=True),
            sa.Column("updated_at", _ts, nullable=False, server_default=sa.func.now()),
        ]

    op.create_table(
        "domains",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("owner", sa.String(120), nullable=False, server_default=""),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        *_enterprise_columns([]),
    )
    op.create_index("ix_domains_slug", "domains", ["slug"])

    op.create_table(
        "capabilities",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("domain_slug", sa.String(120), nullable=True),
        sa.Column("criticality", sa.String(40), nullable=True),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        *_enterprise_columns([]),
    )
    op.create_index("ix_capabilities_slug", "capabilities", ["slug"])

    op.create_table(
        "applications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("application_group_slug", sa.String(120), nullable=True),
        sa.Column("domain_slug", sa.String(120), nullable=True),
        sa.Column("type", sa.String(80), nullable=True),
        sa.Column("architecture_state", sa.String(40), nullable=True),
        sa.Column("lifecycle", sa.String(40), nullable=True),
        sa.Column("criticality", sa.String(40), nullable=True),
        sa.Column("owner", sa.String(120), nullable=False, server_default=""),
        sa.Column(
            "supports_capabilities", sa.Text, nullable=False, server_default="[]"
        ),
        *_enterprise_columns([]),
    )
    op.create_index("ix_applications_slug", "applications", ["slug"])

    op.create_table(
        "application_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(160), nullable=False, unique=True),
        sa.Column("source_app_slug", sa.String(120), nullable=False),
        sa.Column("target_app_slug", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(40), nullable=True),
        *_enterprise_columns([]),
    )
    op.create_index("ix_application_links_slug", "application_links", ["slug"])

    op.create_table(
        "data_objects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("domain_slug", sa.String(120), nullable=True),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        *_enterprise_columns([]),
    )
    op.create_index("ix_data_objects_slug", "data_objects", ["slug"])

    op.create_table(
        "data_domains",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        *_enterprise_columns([]),
    )
    op.create_index("ix_data_domains_slug", "data_domains", ["slug"])

    op.create_table(
        "technology_platforms",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(80), nullable=True),
        sa.Column("owner", sa.String(120), nullable=False, server_default=""),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        *_enterprise_columns([]),
    )
    op.create_index(
        "ix_technology_platforms_slug", "technology_platforms", ["slug"]
    )

    op.create_table(
        "standards",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        *_enterprise_columns([]),
    )
    op.create_index("ix_standards_slug", "standards", ["slug"])

    op.create_table(
        "principles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        *_enterprise_columns([]),
    )
    op.create_index("ix_principles_slug", "principles", ["slug"])

    # --- HLD context links (polymorphic) ----------------------------------
    op.create_table(
        "architecture_context_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer,
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column("object_type", sa.String(40), nullable=False),
        sa.Column("object_slug", sa.String(160), nullable=False),
        sa.Column("created_at", _ts, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "document_id", "object_type", "object_slug",
            name="uq_architecture_context_links",
        ),
    )


def downgrade() -> None:
    op.drop_table("architecture_context_links")
    for table in (
        "principles",
        "standards",
        "technology_platforms",
        "data_domains",
        "data_objects",
        "application_links",
        "applications",
        "capabilities",
        "domains",
    ):
        op.drop_index(f"ix_{table}_slug", table_name=table)
        op.drop_table(table)
    op.drop_constraint(
        "application_groups_slug_key", "application_groups", type_="unique"
    )
    op.create_unique_constraint(
        "application_groups_repository_id_slug_key",
        "application_groups",
        ["repository_id", "slug"],
    )
    op.alter_column(
        "application_groups",
        "repository_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_column("application_groups", "git_path")
    op.drop_column("application_groups", "archimate_type")
    op.drop_column("application_groups", "domain_slug")
