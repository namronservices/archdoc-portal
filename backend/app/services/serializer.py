"""Serialize a Document into the canonical Git file set.

Produced layout (relative to repo root):
    increments/<inc>/hld/hld.md
    increments/<inc>/hld/sections.yaml
    increments/<inc>/hld/toc.yaml
    increments/<inc>/hld/metadata.yaml
    increments/<inc>/hld/reuse-instances.yaml
    increments/<inc>/hld/diagrams/<name>.mmd
    increments/<inc>/hld/diagrams/<name>.svg
    increments/<inc>/hld/forked-blocks/<block_id>.md
"""
from __future__ import annotations

from datetime import datetime, timezone

import yaml
from sqlalchemy.orm import object_session

from app.models import (
    REUSE_FORKED,
    REUSE_SNAPSHOT,
    Diagram,
    Document,
    DocumentReuseInstance,
    DocumentSection,
    ReusableBlock,
)
from app.services.block_library import directive_path
from app.services.block_parser import render_block_file
from app.services.numbering import ordered_children, ordered_roots


def hld_dir(document: Document) -> str:
    """Repo-relative directory holding this document's HLD source."""
    return f"increments/{document.increment.slug}/hld"


def _blocks_by_id(document: Document) -> dict[str, ReusableBlock]:
    db = object_session(document)
    if db is None:
        return {}
    return {b.block_id: b for b in db.query(ReusableBlock).all()}


def _diagrams_for(document: Document, section_id: int) -> list[Diagram]:
    return [d for d in document.diagrams if d.section_id == section_id]


def _reuse_for(document: Document, section_id: int) -> list[DocumentReuseInstance]:
    return sorted(
        (r for r in document.reuse_instances if r.section_id == section_id),
        key=lambda r: r.order_index,
    )


def _reuse_markdown(
    instance: DocumentReuseInstance,
    blocks: dict[str, ReusableBlock],
    resolve: bool,
) -> str:
    """Render one reuse instance.

    ``resolve=False`` keeps linked reuse as a ``{{reuse:...}}`` directive (Git
    source form); ``resolve=True`` expands it to the library block body (export).
    """
    if instance.reuse_mode == REUSE_FORKED:
        fork = (
            blocks.get(instance.derived_block_id)
            if instance.derived_block_id
            else None
        )
        return (fork.body if fork else "").strip()
    if instance.reuse_mode == REUSE_SNAPSHOT:
        return (instance.snapshot_content or "").strip()
    # linked
    library = blocks.get(instance.block_id)
    if resolve:
        return (library.body if library else "").strip()
    path = directive_path(library.git_path) if library else instance.block_id
    version = instance.source_version or (library.version if library else "")
    return f"{{{{reuse:{path}@{version}}}}}"


def _section_markdown(
    document: Document,
    section: DocumentSection,
    level: int,
    blocks: dict[str, ReusableBlock],
    resolve: bool,
) -> str:
    heading = "#" * level
    parts = [f"{heading} {section.number} {section.title}", ""]
    if section.content.strip():
        parts.append(section.content.strip())
        parts.append("")
    for instance in _reuse_for(document, section.id):
        md = _reuse_markdown(instance, blocks, resolve)
        if md:
            parts.append(md)
            parts.append("")
    for diagram in _diagrams_for(document, section.id):
        # Only embed diagrams that have a rendered SVG; unrendered ones are
        # surfaced separately as validation hints.
        if diagram.svg:
            parts.append(f"![{diagram.name}](diagrams/{diagram.name}.svg)")
            parts.append("")
    return "\n".join(parts)


def build_markdown(document: Document, resolve: bool = False) -> str:
    """Assemble the full ``hld.md`` body.

    ``resolve=True`` expands linked reuse directives to their library content
    (used by export); the default keeps directives for the Git source.
    """
    blocks = _blocks_by_id(document)
    out = [f"# {document.title}", ""]
    for chapter in ordered_roots(document):
        out.append(_section_markdown(document, chapter, 2, blocks, resolve))
        for sub in ordered_children(document, chapter.id):
            out.append(_section_markdown(document, sub, 3, blocks, resolve))
    return "\n".join(out).rstrip() + "\n"


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


def build_reuse_instances_yaml(document: Document) -> str:
    rows = []
    for r in sorted(
        document.reuse_instances, key=lambda r: (r.section_id, r.order_index)
    ):
        rows.append(
            {
                "id": r.id,
                "section_id": r.section_id,
                "block_id": r.block_id,
                "reuse_mode": r.reuse_mode,
                "source_version": r.source_version,
                "derived_block_id": r.derived_block_id,
                "status": r.status,
            }
        )
    return yaml.safe_dump(
        {"reuse_instances": rows}, sort_keys=False, allow_unicode=True
    )


def _fork_files(document: Document, base: str) -> dict[str, str]:
    """One Markdown file per local fork under ``forked-blocks/``."""
    db = object_session(document)
    files: dict[str, str] = {}
    if db is None:
        return files
    forks = (
        db.query(ReusableBlock)
        .filter_by(document_id=document.id, derivation_type="fork")
        .all()
    )
    for fork in forks:
        meta = {
            "block_id": fork.block_id,
            "title": fork.title,
            "type": fork.category,
            "version": fork.version,
            "status": fork.status,
            "owner": fork.owner,
            "derived_from": fork.derived_from,
            "derived_from_version": fork.derived_from_version,
            "derivation_type": "fork",
            "scope": fork.scope,
        }
        files[f"{base}/forked-blocks/{fork.block_id}.md"] = render_block_file(
            meta, fork.body
        )
    return files


def build_file_set(document: Document) -> dict[str, str]:
    """Return ``{repo_relative_path: text_content}`` for the whole document."""
    base = hld_dir(document)
    files: dict[str, str] = {
        f"{base}/hld.md": build_markdown(document),
        f"{base}/sections.yaml": build_sections_yaml(document),
        f"{base}/toc.yaml": build_toc_yaml(document),
        f"{base}/metadata.yaml": build_metadata_yaml(document),
        f"{base}/reuse-instances.yaml": build_reuse_instances_yaml(document),
    }
    for diagram in document.diagrams:
        files[f"{base}/diagrams/{diagram.name}.mmd"] = diagram.source or ""
        if diagram.svg:
            files[f"{base}/diagrams/{diagram.name}.svg"] = diagram.svg
    files.update(_fork_files(document, base))
    return files
