"""Shared response builders."""
from __future__ import annotations

from app.models import Document
from app.schemas import DiagramOut, DocumentOut, SectionOut
from app.services.numbering import ordered_children, ordered_roots


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

    return DocumentOut(
        id=document.id,
        increment_id=document.increment_id,
        type=document.type,
        title=document.title,
        git_branch=document.git_branch,
        head_commit=document.head_commit,
        sections=sections,
        diagrams=[DiagramOut.model_validate(d) for d in document.diagrams],
        breadcrumb={
            "repository": repository.name,
            "application_group": group.name,
            "increment": increment.name,
            "document": document.title,
        },
    )
