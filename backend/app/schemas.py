"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Repositories -------------------------------------------------------
class RepositoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=120)


class RepositoryOut(ORMModel):
    id: int
    slug: str
    name: str
    default_branch: str
    created_at: datetime


# --- Application groups -------------------------------------------------
class ApplicationGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=120)
    description: str = ""


class ApplicationGroupOut(ORMModel):
    id: int
    repository_id: int
    slug: str
    name: str
    description: str
    created_at: datetime


# --- Increments ---------------------------------------------------------
class IncrementCreate(BaseModel):
    application_group_id: int
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = Field(default=None, max_length=120)


class IncrementOut(ORMModel):
    id: int
    application_group_id: int
    slug: str
    name: str
    status: str
    created_at: datetime


# --- HLD documents ------------------------------------------------------
class HldCreate(BaseModel):
    title: str | None = Field(default=None, max_length=300)


class SectionOut(ORMModel):
    id: int
    parent_id: int | None
    order_index: int
    number: str
    title: str
    content: str
    kind: str


class SectionUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    content: str | None = None


class ChapterCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = ""


class SubchapterCreate(BaseModel):
    parent_id: int
    title: str = Field(min_length=1, max_length=300)
    content: str = ""


class StructureItem(BaseModel):
    id: int
    parent_id: int | None = None
    order_index: int


class StructureUpdate(BaseModel):
    items: list[StructureItem]


class CommitInfoOut(BaseModel):
    hash: str
    short_hash: str
    message: str
    author: str
    committed_at: str


class DiagramOut(ORMModel):
    id: int
    document_id: int
    section_id: int | None
    name: str
    source: str
    svg: str
    render_status: str
    last_error: str


class DocumentOut(ORMModel):
    id: int
    increment_id: int
    type: str
    title: str
    git_branch: str
    head_commit: str | None
    sections: list[SectionOut]
    diagrams: list[DiagramOut]
    breadcrumb: dict[str, str]


# --- Diagrams -----------------------------------------------------------
class DiagramCreate(BaseModel):
    section_id: int | None = None
    name: str = Field(min_length=1, max_length=120)
    source: str = ""


class DiagramUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    source: str | None = None
    section_id: int | None = None


# --- Export & validation ------------------------------------------------
class ExportRequest(BaseModel):
    format: str = Field(default="docx", pattern="^(docx|pdf)$")


class ExportJobOut(ORMModel):
    id: int
    document_id: int
    format: str
    status: str
    artifact_path: str | None
    error: str
    created_at: datetime


class ValidationItem(BaseModel):
    severity: str
    message: str
    section_id: int | None = None


class ValidationOut(BaseModel):
    document_id: int
    results: list[ValidationItem]
