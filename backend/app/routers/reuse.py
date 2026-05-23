"""Reusable block insertion and reuse-instance management for HLD documents."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    DOC_TYPE_HLD,
    DOC_TYPE_INTEGRATION,
    REUSE_FORKED,
    REUSE_LINKED,
    REUSE_SNAPSHOT,
    Document,
    DocumentReuseInstance,
    DocumentSection,
    ReusableBlock,
)
from app.schemas import (
    DocumentOut,
    ForkRequest,
    InsertReuseRequest,
    ReuseInstanceOut,
    ReuseInstanceUpdate,
)
from app.services.block_library import sync_library
from app.views import build_document_out, reuse_instance_out

router = APIRouter(tags=["reuse"])


def _get_hld(document_id: int, db: Session) -> Document:
    """Fetch a document that can embed reusable blocks (HLD or integration)."""
    document = db.get(Document, document_id)
    if document is None or document.type not in (
        DOC_TYPE_HLD,
        DOC_TYPE_INTEGRATION,
    ):
        raise HTTPException(404, "Document not found")
    return document


def _get_section(document: Document, section_id: int) -> DocumentSection:
    section = next((s for s in document.sections if s.id == section_id), None)
    if section is None:
        raise HTTPException(404, "Section not found")
    return section


def _library_block(block_id: str, db: Session) -> ReusableBlock:
    """Fetch a library block by id, syncing the library once if missing."""
    block = (
        db.query(ReusableBlock)
        .filter_by(block_id=block_id, document_id=None)
        .first()
    )
    if block is None:
        sync_library(db)
        block = (
            db.query(ReusableBlock)
            .filter_by(block_id=block_id, document_id=None)
            .first()
        )
    if block is None:
        raise HTTPException(404, "Reusable block not found")
    return block


def _next_order(document_id: int, section_id: int, db: Session) -> int:
    return (
        db.query(DocumentReuseInstance)
        .filter_by(document_id=document_id, section_id=section_id)
        .count()
    )


def _blocks_by_id(db: Session) -> dict[str, ReusableBlock]:
    return {b.block_id: b for b in db.query(ReusableBlock).all()}


@router.post(
    "/api/hlds/{document_id}/reuse/{block_id}/insert-linked",
    response_model=DocumentOut,
)
def insert_linked(
    document_id: int,
    block_id: str,
    payload: InsertReuseRequest,
    db: Session = Depends(get_db),
):
    document = _get_hld(document_id, db)
    section = _get_section(document, payload.section_id)
    block = _library_block(block_id, db)
    db.add(
        DocumentReuseInstance(
            document_id=document_id,
            section_id=section.id,
            block_id=block_id,
            reuse_mode=REUSE_LINKED,
            source_version=block.version,
            order_index=_next_order(document_id, section.id, db),
        )
    )
    db.commit()
    db.refresh(document)
    return build_document_out(document)


@router.post(
    "/api/hlds/{document_id}/reuse/{block_id}/insert-snapshot",
    response_model=DocumentOut,
)
def insert_snapshot(
    document_id: int,
    block_id: str,
    payload: InsertReuseRequest,
    db: Session = Depends(get_db),
):
    document = _get_hld(document_id, db)
    section = _get_section(document, payload.section_id)
    block = _library_block(block_id, db)
    db.add(
        DocumentReuseInstance(
            document_id=document_id,
            section_id=section.id,
            block_id=block_id,
            reuse_mode=REUSE_SNAPSHOT,
            source_version=block.version,
            snapshot_content=block.body,
            order_index=_next_order(document_id, section.id, db),
        )
    )
    db.commit()
    db.refresh(document)
    return build_document_out(document)


@router.post(
    "/api/hlds/{document_id}/reuse/{block_id}/fork", response_model=DocumentOut
)
def fork_block(
    document_id: int,
    block_id: str,
    payload: ForkRequest,
    db: Session = Depends(get_db),
):
    document = _get_hld(document_id, db)
    section = _get_section(document, payload.section_id)
    source = _library_block(block_id, db)

    base_id = payload.new_block_id or f"{block_id}-fork"
    new_id, n = base_id, 1
    while db.query(ReusableBlock).filter_by(block_id=new_id).first() is not None:
        n += 1
        new_id = f"{base_id}-{n}"

    db.add(
        ReusableBlock(
            block_id=new_id,
            title=payload.title
            or f"{source.title} — {document.increment.name} Variant",
            category=source.category,
            version="0.1",
            status="draft",
            owner="solution-architecture",
            tags=source.tags,
            body=source.body,
            scope=payload.scope,
            derived_from=source.block_id,
            derived_from_version=source.version,
            derivation_type="fork",
            document_id=document_id,
        )
    )
    db.add(
        DocumentReuseInstance(
            document_id=document_id,
            section_id=section.id,
            block_id=block_id,
            reuse_mode=REUSE_FORKED,
            source_version=source.version,
            derived_block_id=new_id,
            order_index=_next_order(document_id, section.id, db),
        )
    )
    db.commit()
    db.refresh(document)
    return build_document_out(document)


@router.get(
    "/api/hlds/{document_id}/reuse", response_model=list[ReuseInstanceOut]
)
def list_reuse(document_id: int, db: Session = Depends(get_db)):
    document = _get_hld(document_id, db)
    blocks = _blocks_by_id(db)
    instances = sorted(
        document.reuse_instances, key=lambda i: (i.section_id, i.order_index)
    )
    return [reuse_instance_out(i, blocks) for i in instances]


@router.get(
    "/api/hlds/{document_id}/reuse/{reuse_instance_id}",
    response_model=ReuseInstanceOut,
)
def get_reuse(
    document_id: int, reuse_instance_id: int, db: Session = Depends(get_db)
):
    _get_hld(document_id, db)
    instance = db.get(DocumentReuseInstance, reuse_instance_id)
    if instance is None or instance.document_id != document_id:
        raise HTTPException(404, "Reuse instance not found")
    return reuse_instance_out(instance, _blocks_by_id(db))


@router.put(
    "/api/hlds/{document_id}/reuse/{reuse_instance_id}",
    response_model=ReuseInstanceOut,
)
def update_reuse(
    document_id: int,
    reuse_instance_id: int,
    payload: ReuseInstanceUpdate,
    db: Session = Depends(get_db),
):
    """Edit a reuse instance — fork body, rationale, or status."""
    _get_hld(document_id, db)
    instance = db.get(DocumentReuseInstance, reuse_instance_id)
    if instance is None or instance.document_id != document_id:
        raise HTTPException(404, "Reuse instance not found")
    if payload.rationale is not None:
        instance.rationale = payload.rationale
    if payload.status is not None:
        instance.status = payload.status
    if payload.body is not None:
        if instance.reuse_mode == REUSE_FORKED and instance.derived_block_id:
            fork = (
                db.query(ReusableBlock)
                .filter_by(block_id=instance.derived_block_id)
                .first()
            )
            if fork is not None:
                fork.body = payload.body
        elif instance.reuse_mode == REUSE_SNAPSHOT:
            instance.snapshot_content = payload.body
        else:
            raise HTTPException(400, "Linked reuse content cannot be edited")
    db.commit()
    db.refresh(instance)
    return reuse_instance_out(instance, _blocks_by_id(db))


@router.delete(
    "/api/hlds/{document_id}/reuse/{reuse_instance_id}",
    response_model=DocumentOut,
)
def delete_reuse(
    document_id: int, reuse_instance_id: int, db: Session = Depends(get_db)
):
    document = _get_hld(document_id, db)
    instance = db.get(DocumentReuseInstance, reuse_instance_id)
    if instance is None or instance.document_id != document_id:
        raise HTTPException(404, "Reuse instance not found")
    fork_id = (
        instance.derived_block_id
        if instance.reuse_mode == REUSE_FORKED
        else None
    )
    db.delete(instance)
    if fork_id:
        fork = db.query(ReusableBlock).filter_by(block_id=fork_id).first()
        if fork is not None:
            db.delete(fork)
    db.commit()
    db.refresh(document)
    return build_document_out(document)
