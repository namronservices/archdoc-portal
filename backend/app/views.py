"""Shared response builders."""
from __future__ import annotations

import json

from sqlalchemy.orm import object_session

from app.models import (
    REUSE_FORKED,
    REUSE_SNAPSHOT,
    Document,
    DocumentReuseInstance,
    ReusableBlock,
)
from app.schemas import (
    DiagramOut,
    DocumentOut,
    ReusableBlockOut,
    ReuseInstanceOut,
    SectionOut,
)
from app.services.numbering import ordered_children, ordered_roots


def block_out(block: ReusableBlock) -> ReusableBlockOut:
    """Convert a ``ReusableBlock`` row to its API schema (tags JSON → list)."""
    try:
        tags = json.loads(block.tags or "[]")
    except (ValueError, TypeError):
        tags = []
    return ReusableBlockOut(
        id=block.id,
        block_id=block.block_id,
        title=block.title,
        category=block.category,
        version=block.version,
        status=block.status,
        owner=block.owner,
        tags=tags if isinstance(tags, list) else [],
        body=block.body,
        scope=block.scope,
        derived_from=block.derived_from,
        derived_from_version=block.derived_from_version,
        derivation_type=block.derivation_type,
        document_id=block.document_id,
    )


def reuse_instance_out(
    instance: DocumentReuseInstance, blocks: dict[str, ReusableBlock]
) -> ReuseInstanceOut:
    """Resolve a reuse instance into a display-ready schema.

    ``blocks`` maps ``block_id`` → row for every reusable block (library + forks).
    """
    library = blocks.get(instance.block_id)
    fork = (
        blocks.get(instance.derived_block_id) if instance.derived_block_id else None
    )
    if instance.reuse_mode == REUSE_FORKED:
        title = (
            fork.title if fork else (instance.derived_block_id or instance.block_id)
        )
        body = fork.body if fork else ""
        broken = fork is None
    elif instance.reuse_mode == REUSE_SNAPSHOT:
        title = library.title if library else instance.block_id
        body = instance.snapshot_content
        broken = False
    else:  # linked
        title = library.title if library else instance.block_id
        body = library.body if library else ""
        broken = library is None
    return ReuseInstanceOut(
        id=instance.id,
        document_id=instance.document_id,
        section_id=instance.section_id,
        block_id=instance.block_id,
        reuse_mode=instance.reuse_mode,
        source_version=instance.source_version,
        derived_block_id=instance.derived_block_id,
        rationale=instance.rationale,
        status=instance.status,
        order_index=instance.order_index,
        title=title,
        body=body,
        library_version=library.version if library else None,
        library_status=library.status if library else None,
        broken=broken,
    )


def build_document_out(document: Document) -> DocumentOut:
    """Assemble the full editor payload for a document."""
    sections: list[SectionOut] = []
    for chapter in ordered_roots(document):
        sections.append(SectionOut.model_validate(chapter))
        for sub in ordered_children(document, chapter.id):
            sections.append(SectionOut.model_validate(sub))

    increment = document.increment
    group = increment.application_group
    repository = group.repository

    db = object_session(document)
    blocks: dict[str, ReusableBlock] = {}
    if db is not None:
        blocks = {b.block_id: b for b in db.query(ReusableBlock).all()}
    instances = sorted(
        document.reuse_instances, key=lambda i: (i.section_id, i.order_index)
    )

    return DocumentOut(
        id=document.id,
        increment_id=document.increment_id,
        type=document.type,
        title=document.title,
        git_branch=document.git_branch,
        head_commit=document.head_commit,
        sections=sections,
        diagrams=[DiagramOut.model_validate(d) for d in document.diagrams],
        reuse_instances=[reuse_instance_out(i, blocks) for i in instances],
        breadcrumb={
            "repository": repository.name,
            "application_group": group.name,
            "increment": increment.name,
            "document": document.title,
        },
    )
