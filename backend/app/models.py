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


# Section kinds — drives the required/template/custom marker in the UI.
KIND_TEMPLATE_REQUIRED = "template_required"
KIND_TEMPLATE_OPTIONAL = "template_optional"
KIND_CUSTOM = "custom"


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
