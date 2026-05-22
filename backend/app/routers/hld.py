"""HLD document, section, chapter, and structure endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    KIND_CUSTOM,
    ArchitectureIncrement,
    Document,
    DocumentSection,
)
from app.schemas import (
    ChapterCreate,
    DocumentOut,
    HldCreate,
    SectionOut,
    SectionUpdate,
    StructureUpdate,
    SubchapterCreate,
)
from app.services.git_adapter import git_adapter
from app.services.numbering import renumber
from app.services.serializer import build_file_set
from app.services.template import apply_hld_template, template_title
from app.views import build_document_out

router = APIRouter(tags=["hld"])


def _get_hld(document_id: int, db: Session) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.type != "hld":
        raise HTTPException(404, "HLD document not found")
    return document


def _repo_slug(document: Document) -> str:
    return document.increment.application_group.repository.slug


@router.post(
    "/api/increments/{increment_id}/hld",
    response_model=DocumentOut,
    status_code=201,
)
def create_hld(
    increment_id: int, payload: HldCreate, db: Session = Depends(get_db)
):
    increment = db.get(ArchitectureIncrement, increment_id)
    if increment is None:
        raise HTTPException(404, "Increment not found")
    if db.query(Document).filter_by(increment_id=increment_id, type="hld").first():
        raise HTTPException(409, "This increment already has an HLD")

    document = Document(
        increment_id=increment_id,
        type="hld",
        title=payload.title or f"{increment.name} — {template_title()}",
    )
    db.add(document)
    db.flush()
    apply_hld_template(db, document)
    db.flush()

    commit = git_adapter.commit(
        _repo_slug(document),
        build_file_set(document),
        f"Create HLD for increment '{increment.name}'",
    )
    document.head_commit = commit.short_hash
    db.commit()
    db.refresh(document)
    return build_document_out(document)


@router.get("/api/hlds/{document_id}", response_model=DocumentOut)
def get_hld(document_id: int, db: Session = Depends(get_db)):
    return build_document_out(_get_hld(document_id, db))


@router.put(
    "/api/hlds/{document_id}/sections/{section_id}", response_model=SectionOut
)
def update_section(
    document_id: int,
    section_id: int,
    payload: SectionUpdate,
    db: Session = Depends(get_db),
):
    _get_hld(document_id, db)
    section = db.get(DocumentSection, section_id)
    if section is None or section.document_id != document_id:
        raise HTTPException(404, "Section not found")
    if payload.title is not None:
        section.title = payload.title
    if payload.content is not None:
        section.content = payload.content
    db.commit()
    db.refresh(section)
    return SectionOut.model_validate(section)


@router.post("/api/hlds/{document_id}/chapters", response_model=DocumentOut)
def add_chapter(
    document_id: int, payload: ChapterCreate, db: Session = Depends(get_db)
):
    document = _get_hld(document_id, db)
    roots = [s for s in document.sections if s.parent_id is None]
    chapter = DocumentSection(
        document=document,
        parent_id=None,
        order_index=len(roots),
        title=payload.title,
        content=payload.content,
        kind=KIND_CUSTOM,
    )
    db.add(chapter)
    db.flush()
    renumber(db, document)
    db.commit()
    db.refresh(document)
    return build_document_out(document)


@router.post("/api/hlds/{document_id}/subchapters", response_model=DocumentOut)
def add_subchapter(
    document_id: int, payload: SubchapterCreate, db: Session = Depends(get_db)
):
    document = _get_hld(document_id, db)
    parent = db.get(DocumentSection, payload.parent_id)
    if parent is None or parent.document_id != document_id:
        raise HTTPException(404, "Parent chapter not found")
    if parent.parent_id is not None:
        raise HTTPException(400, "Sub-chapters can only be added to chapters")
    siblings = [s for s in document.sections if s.parent_id == parent.id]
    sub = DocumentSection(
        document=document,
        parent_id=parent.id,
        order_index=len(siblings),
        title=payload.title,
        content=payload.content,
        kind=KIND_CUSTOM,
    )
    db.add(sub)
    db.flush()
    renumber(db, document)
    db.commit()
    db.refresh(document)
    return build_document_out(document)


@router.put("/api/hlds/{document_id}/structure", response_model=DocumentOut)
def update_structure(
    document_id: int, payload: StructureUpdate, db: Session = Depends(get_db)
):
    document = _get_hld(document_id, db)
    by_id = {s.id: s for s in document.sections}
    for item in payload.items:
        section = by_id.get(item.id)
        if section is None:
            raise HTTPException(404, f"Section {item.id} not found")
        section.parent_id = item.parent_id
        section.order_index = item.order_index
    db.flush()
    renumber(db, document)
    db.commit()
    db.refresh(document)
    return build_document_out(document)
