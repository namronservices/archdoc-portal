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


# --- Reusable blocks ----------------------------------------------------
class ReusableBlockOut(BaseModel):
    id: int
    block_id: str
    title: str
    category: str
    version: str
    status: str
    owner: str
    tags: list[str]
    body: str
    scope: str | None = None
    derived_from: str | None = None
    derived_from_version: str = ""
    derivation_type: str | None = None
    document_id: int | None = None


class ReuseInstanceOut(BaseModel):
    id: int
    document_id: int
    section_id: int
    block_id: str
    reuse_mode: str
    source_version: str
    derived_block_id: str | None = None
    rationale: str
    status: str
    order_index: int
    title: str
    body: str
    library_version: str | None = None
    library_status: str | None = None
    broken: bool = False


class InsertReuseRequest(BaseModel):
    section_id: int


class ForkRequest(BaseModel):
    section_id: int
    new_block_id: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=300)
    scope: str = Field(default="hld-local", max_length=40)


class ReuseInstanceUpdate(BaseModel):
    body: str | None = None
    rationale: str | None = None
    status: str | None = None


class BlockCompareOut(BaseModel):
    source: ReusableBlockOut | None = None
    derived: ReusableBlockOut | None = None


class DocumentOut(ORMModel):
    id: int
    increment_id: int
    type: str
    title: str
    git_branch: str
    head_commit: str | None
    sections: list[SectionOut]
    diagrams: list[DiagramOut]
    reuse_instances: list[ReuseInstanceOut]
    linked_integrations: list[LinkedIntegrationOut] = []
    integration_ref: LinkedIntegrationOut | None = None
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


# --- Integrations -------------------------------------------------------
class IntegrationCreate(BaseModel):
    type: str = Field(max_length=20)
    name: str = Field(min_length=1, max_length=200)
    integration_id: str | None = Field(default=None, max_length=120)
    source_application: str = Field(default="", max_length=200)
    target_application: str = Field(default="", max_length=200)
    required: bool = True
    create_document: bool = False


class IntegrationUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    source_application: str | None = Field(default=None, max_length=200)
    target_application: str | None = Field(default=None, max_length=200)
    required: bool | None = None
    status: str | None = Field(default=None, max_length=40)
    metadata: dict | None = None


class IntegrationListItem(BaseModel):
    id: int
    increment_id: int
    integration_id: str
    name: str
    type: str
    type_label: str
    source_application: str
    target_application: str
    required: bool
    status: str
    document_id: int | None = None
    document_filename: str | None = None


class MetadataFieldSpec(BaseModel):
    key: str
    label: str
    kind: str
    options: list[str] | None = None


class LinkedHldOut(BaseModel):
    document_id: int
    title: str


class IntegrationOut(BaseModel):
    id: int
    increment_id: int
    integration_id: str
    name: str
    type: str
    type_label: str
    source_application: str
    target_application: str
    required: bool
    status: str
    document_id: int | None = None
    metadata: dict
    metadata_schema: list[MetadataFieldSpec]
    contract_filename: str
    contract_path: str
    has_contract: bool
    contract_format: str
    linked_hlds: list[LinkedHldOut]


class ContractIn(BaseModel):
    filename: str = Field(min_length=1, max_length=200)
    content: str = ""


class ContractOut(BaseModel):
    filename: str
    path: str
    content: str


class IntegrationCreateMissingOut(BaseModel):
    created: list[IntegrationListItem]


class IntegrationValidationOut(BaseModel):
    integration_id: int
    results: list[ValidationItem]


class LinkedIntegrationOut(BaseModel):
    id: int
    integration_id: str
    name: str
    type: str
    type_label: str
    source_application: str
    target_application: str
    status: str
    document_id: int | None = None
