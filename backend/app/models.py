"""SQLAlchemy ORM models — operational metadata only.

Canonical document source (Markdown / YAML / Mermaid) lives in Git; these tables
hold the live working state and pointers needed to drive the editor and exports.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Repository(Base):
    """A Git-backed architecture source repository."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    git_path: Mapped[str] = mapped_column(String(500))
    default_branch: Mapped[str] = mapped_column(String(80), default="main")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    application_groups: Mapped[list["ApplicationGroup"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )


class ApplicationGroup(Base):
    """A TOGAF-style application group within a repository."""

    __tablename__ = "application_groups"
    __table_args__ = (UniqueConstraint("repository_id", "slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id"))
    slug: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    repository: Mapped[Repository] = relationship(back_populates="application_groups")
    increments: Mapped[list["ArchitectureIncrement"]] = relationship(
        back_populates="application_group", cascade="all, delete-orphan"
    )


class ArchitectureIncrement(Base):
    """A specific architecture increment (delivery scope) under an application group."""

    __tablename__ = "architecture_increments"
    __table_args__ = (UniqueConstraint("application_group_id", "slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    application_group_id: Mapped[int] = mapped_column(
        ForeignKey("application_groups.id")
    )
    slug: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    application_group: Mapped[ApplicationGroup] = relationship(
        back_populates="increments"
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="increment", cascade="all, delete-orphan"
    )


class Document(Base):
    """A document (Phase 1: HLD) belonging to an increment."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    increment_id: Mapped[int] = mapped_column(ForeignKey("architecture_increments.id"))
    type: Mapped[str] = mapped_column(String(40), default="hld")
    title: Mapped[str] = mapped_column(String(300))
    git_branch: Mapped[str] = mapped_column(String(80), default="main")
    head_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    increment: Mapped[ArchitectureIncrement] = relationship(
        back_populates="documents"
    )
    sections: Mapped[list["DocumentSection"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    diagrams: Mapped[list["Diagram"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    reuse_instances: Mapped[list["DocumentReuseInstance"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    integration: Mapped["Integration | None"] = relationship(
        back_populates="document",
        foreign_keys="Integration.document_id",
        uselist=False,
    )


# Section kinds — drives the required/template/custom marker in the UI.
KIND_TEMPLATE_REQUIRED = "template_required"
KIND_TEMPLATE_OPTIONAL = "template_optional"
KIND_CUSTOM = "custom"

# Document types.
DOC_TYPE_HLD = "hld"
DOC_TYPE_INTEGRATION = "integration"

# Integration types — gRPC is first-class alongside the others.
INTEGRATION_TYPES = (
    "GRPC",
    "KAFKA",
    "MQ",
    "SOAP",
    "REST",
    "FILE",
    "BATCH",
)


class DocumentSection(Base):
    """A chapter or sub-chapter of a document. Self-referential tree."""

    __tablename__ = "document_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_sections.id"), nullable=True
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    number: Mapped[str] = mapped_column(String(20), default="")
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(40), default=KIND_CUSTOM)
    git_path: Mapped[str] = mapped_column(String(500), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    document: Mapped[Document] = relationship(back_populates="sections")


class Diagram(Base):
    """A Mermaid diagram block. Source (.mmd) and rendered (.svg) live in Git."""

    __tablename__ = "diagrams"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    section_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_sections.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(Text, default="")
    mmd_path: Mapped[str] = mapped_column(String(500), default="")
    svg_path: Mapped[str] = mapped_column(String(500), default="")
    svg: Mapped[str] = mapped_column(Text, default="")
    render_status: Mapped[str] = mapped_column(String(40), default="pending")
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    document: Mapped[Document] = relationship(back_populates="diagrams")


class ExportJob(Base):
    """A DOCX/PDF export run."""

    __tablename__ = "export_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    format: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(40), default="pending")
    artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ValidationResult(Base):
    """A validation hint (Mermaid error, missing required section, ...)."""

    __tablename__ = "validation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    section_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_sections.id"), nullable=True
    )
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# Reuse modes — how a reusable block is embedded in a document.
REUSE_LINKED = "linked"
REUSE_SNAPSHOT = "snapshot"
REUSE_FORKED = "forked"


class ReusableBlock(Base):
    """A reusable architecture block.

    Two flavours share this table:
      * library blocks — synced from the shared ``architecture-library`` repo
        (``document_id`` is NULL);
      * local forks — derived from a library block and scoped to one document
        (``document_id`` set, ``derivation_type`` = ``fork``).
    """

    __tablename__ = "reusable_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(80), default="")
    version: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    owner: Mapped[str] = mapped_column(String(120), default="")
    tags: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    body: Mapped[str] = mapped_column(Text, default="")
    git_path: Mapped[str] = mapped_column(String(500), default="")
    scope: Mapped[str | None] = mapped_column(String(40), nullable=True)
    derived_from: Mapped[str | None] = mapped_column(String(200), nullable=True)
    derived_from_version: Mapped[str] = mapped_column(String(40), default="")
    derivation_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class DocumentReuseInstance(Base):
    """An occurrence of a reusable block embedded in a document section."""

    __tablename__ = "document_reuse_instances"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    section_id: Mapped[int] = mapped_column(ForeignKey("document_sections.id"))
    block_id: Mapped[str] = mapped_column(String(200))
    reuse_mode: Mapped[str] = mapped_column(String(20))
    source_version: Mapped[str] = mapped_column(String(40), default="")
    derived_block_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    snapshot_content: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="active")
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    document: Mapped[Document] = relationship(back_populates="reuse_instances")


class Integration(Base):
    """An integration belonging to an architecture increment.

    Holds type-aware integration metadata and an optional pointer to the
    integration *document* (a ``Document`` with ``type == 'integration'``).
    ``document_id`` is NULL while the integration is only *declared* — listed
    as required but not yet authored.
    """

    __tablename__ = "integrations"
    __table_args__ = (UniqueConstraint("increment_id", "integration_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    increment_id: Mapped[int] = mapped_column(
        ForeignKey("architecture_increments.id")
    )
    integration_id: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(20))  # GRPC, KAFKA, MQ, SOAP, ...
    source_application: Mapped[str] = mapped_column(String(200), default="")
    target_application: Mapped[str] = mapped_column(String(200), default="")
    required: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    contract_filename: Mapped[str] = mapped_column(String(200), default="")
    contract_path: Mapped[str] = mapped_column(String(500), default="")
    contract_content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    increment: Mapped[ArchitectureIncrement] = relationship()
    document: Mapped[Document | None] = relationship(
        back_populates="integration", foreign_keys=[document_id]
    )


class DocumentIntegrationLink(Base):
    """A linked reference from an HLD document to an integration."""

    __tablename__ = "document_integration_links"
    __table_args__ = (UniqueConstraint("document_id", "integration_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))
    integration_id: Mapped[int] = mapped_column(ForeignKey("integrations.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
