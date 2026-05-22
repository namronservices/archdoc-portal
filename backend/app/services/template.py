"""HLD template generation — turns ``hld_template.yaml`` into document sections."""
from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.models import Document, DocumentSection

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "hld_template.yaml"


def load_template() -> dict:
    """Load the default HLD template definition."""
    with TEMPLATE_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def template_title() -> str:
    return load_template().get("title", "High-Level Design")


def apply_hld_template(db: Session, document: Document) -> list[DocumentSection]:
    """Create the template's chapters and sub-chapters for ``document``.

    Sections are flushed (not committed) so callers can extend the transaction.
    """
    template = load_template()
    sections: list[DocumentSection] = []

    for ch_idx, chapter in enumerate(template.get("chapters", [])):
        number = str(ch_idx + 1)
        section = DocumentSection(
            document=document,
            parent_id=None,
            order_index=ch_idx,
            number=number,
            title=chapter["title"],
            content=(chapter.get("content") or "").strip(),
            kind=chapter.get("kind", "template_optional"),
        )
        db.add(section)
        db.flush()  # assign id for child parent_id
        sections.append(section)

        for sub_idx, sub in enumerate(chapter.get("subchapters", []) or []):
            sub_section = DocumentSection(
                document=document,
                parent_id=section.id,
                order_index=sub_idx,
                number=f"{number}.{sub_idx + 1}",
                title=sub["title"],
                content=(sub.get("content") or "").strip(),
                kind=sub.get("kind", "template_optional"),
            )
            db.add(sub_section)
            db.flush()
            sections.append(sub_section)

    return sections
