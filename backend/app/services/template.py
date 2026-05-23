"""Document template generation — turns template YAML into document sections.

Templates live under ``app/templates``: the HLD template at ``hld_template.yaml``
and per-type integration templates under ``integration/<name>.yaml``.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.models import Document, DocumentSection

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
HLD_TEMPLATE_PATH = TEMPLATES_DIR / "hld_template.yaml"


def load_template(name: str = "hld") -> dict:
    """Load a template definition by name.

    ``name='hld'`` loads the HLD template; any other name loads
    ``integration/<name>.yaml``.
    """
    if name == "hld":
        path = HLD_TEMPLATE_PATH
    else:
        path = TEMPLATES_DIR / "integration" / f"{name}.yaml"
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def template_title(name: str = "hld") -> str:
    return load_template(name).get("title", "Document")


def apply_template(
    db: Session, document: Document, name: str = "hld"
) -> list[DocumentSection]:
    """Create the named template's chapters and sub-chapters for ``document``.

    Sections are flushed (not committed) so callers can extend the transaction.
    """
    template = load_template(name)
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


def apply_hld_template(db: Session, document: Document) -> list[DocumentSection]:
    """Backwards-compatible wrapper: apply the default HLD template."""
    return apply_template(db, document, "hld")
