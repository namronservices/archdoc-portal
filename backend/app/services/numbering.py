"""Section ordering and numbering helpers (Phase 1: two levels deep)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Document, DocumentSection


def ordered_roots(document: Document) -> list[DocumentSection]:
    return sorted(
        (s for s in document.sections if s.parent_id is None),
        key=lambda s: s.order_index,
    )


def ordered_children(document: Document, parent_id: int) -> list[DocumentSection]:
    return sorted(
        (s for s in document.sections if s.parent_id == parent_id),
        key=lambda s: s.order_index,
    )


def renumber(db: Session, document: Document) -> None:
    """Recompute ``order_index`` and ``number`` for every section of a document."""
    for ch_idx, chapter in enumerate(ordered_roots(document)):
        chapter.order_index = ch_idx
        chapter.number = str(ch_idx + 1)
        for sub_idx, sub in enumerate(ordered_children(document, chapter.id)):
            sub.order_index = sub_idx
            sub.number = f"{ch_idx + 1}.{sub_idx + 1}"
    db.flush()
