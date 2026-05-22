"""Serialize a Document into the canonical Git file set.

Produced layout (relative to repo root):
    increments/<inc>/hld/hld.md
    increments/<inc>/hld/sections.yaml
    increments/<inc>/hld/toc.yaml
    increments/<inc>/hld/metadata.yaml
    increments/<inc>/hld/diagrams/<name>.mmd
    increments/<inc>/hld/diagrams/<name>.svg
"""
from __future__ import annotations

from datetime import datetime, timezone

import yaml

from app.models import Diagram, Document, DocumentSection
from app.services.numbering import ordered_children, ordered_roots


def hld_dir(document: Document) -> str:
    """Repo-relative directory holding this document's HLD source."""
    return f"increments/{document.increment.slug}/hld"


def _diagrams_for(document: Document, section_id: int) -> list[Diagram]:
    return [d for d in document.diagrams if d.section_id == section_id]


def _section_markdown(document: Document, section: DocumentSection, level: int) -> str:
    heading = "#" * level
    parts = [f"{heading} {section.number} {section.title}", ""]
    if section.content.strip():
        parts.append(section.content.strip())
        parts.append("")
    for diagram in _diagrams_for(document, section.id):
        # Only embed diagrams that have a rendered SVG; unrendered ones are
        # surfaced separately as validation hints.
        if diagram.svg:
            parts.append(f"![{diagram.name}](diagrams/{diagram.name}.svg)")
            parts.append("")
    return "\n".join(parts)


def build_markdown(document: Document) -> str:
    """Assemble the full ``hld.md`` document body."""
    blocks = [f"# {document.title}", ""]
    for chapter in ordered_roots(document):
        blocks.append(_section_markdown(document, chapter, level=2))
        for sub in ordered_children(document, chapter.id):
            blocks.append(_section_markdown(document, sub, level=3))
    return "\n".join(blocks).rstrip() + "\n"


def build_sections_yaml(document: Document) -> str:
    rows = []
    for chapter in ordered_roots(document):
        rows.append(
            {
                "id": chapter.id,
                "number": chapter.number,
                "title": chapter.title,
                "kind": chapter.kind,
                "subchapters": [
                    {
                        "id": sub.id,
                        "number": sub.number,
                        "title": sub.title,
                        "kind": sub.kind,
                    }
                    for sub in ordered_children(document, chapter.id)
                ],
            }
        )
    return yaml.safe_dump({"sections": rows}, sort_keys=False, allow_unicode=True)


def build_toc_yaml(document: Document) -> str:
    entries = []
    for chapter in ordered_roots(document):
        entries.append({"number": chapter.number, "title": chapter.title})
        for sub in ordered_children(document, chapter.id):
            entries.append({"number": sub.number, "title": sub.title})
    return yaml.safe_dump({"toc": entries}, sort_keys=False, allow_unicode=True)


def build_metadata_yaml(document: Document) -> str:
    meta = {
        "title": document.title,
        "type": document.type,
        "increment": document.increment.slug,
        "application_group": document.increment.application_group.slug,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)


def build_file_set(document: Document) -> dict[str, str]:
    """Return ``{repo_relative_path: text_content}`` for the whole document."""
    base = hld_dir(document)
    files: dict[str, str] = {
        f"{base}/hld.md": build_markdown(document),
        f"{base}/sections.yaml": build_sections_yaml(document),
        f"{base}/toc.yaml": build_toc_yaml(document),
        f"{base}/metadata.yaml": build_metadata_yaml(document),
    }
    for diagram in document.diagrams:
        files[f"{base}/diagrams/{diagram.name}.mmd"] = diagram.source or ""
        if diagram.svg:
            files[f"{base}/diagrams/{diagram.name}.svg"] = diagram.svg
    return files
