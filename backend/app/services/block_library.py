"""Shared architecture-library repo: bootstrap, seed, and sync into the DB.

The reusable-block library lives in its own Git repo (slug
``architecture-library``) so it can be shared across every project repository.
``sync_library`` mirrors its parsed contents into the ``reusable_blocks`` table
that drives the editor's block browser.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import ReusableBlock
from app.services.block_parser import parse_block_file
from app.services.git_adapter import git_adapter

LIBRARY_SLUG = "architecture-library"
LIBRARY_ROOT = "reusable-blocks"
SEED_DIR = Path(__file__).resolve().parent.parent / "seed" / "reusable-blocks"


def directive_path(git_path: str) -> str:
    """Repo-relative library path → directive slug, e.g. ``security/mtls-standard``."""
    rel = git_path
    if rel.startswith(f"{LIBRARY_ROOT}/"):
        rel = rel[len(LIBRARY_ROOT) + 1 :]
    if rel.endswith(".md"):
        rel = rel[:-3]
    return rel


def ensure_library() -> None:
    """Create the shared library repo and seed sample blocks (idempotent)."""
    git_adapter.init_repository(LIBRARY_SLUG)
    if git_adapter.read_file(LIBRARY_SLUG, f"{LIBRARY_ROOT}/.seeded") is not None:
        return
    files: dict[str, str] = {f"{LIBRARY_ROOT}/.seeded": "1\n"}
    for path in sorted(SEED_DIR.rglob("*.md")):
        rel = path.relative_to(SEED_DIR).as_posix()
        files[f"{LIBRARY_ROOT}/{rel}"] = path.read_text(encoding="utf-8")
    git_adapter.commit(LIBRARY_SLUG, files, "Seed reusable block library")


def sync_library(db: Session) -> list[ReusableBlock]:
    """Scan the library working tree and upsert library rows; return them."""
    ensure_library()
    root = Path(git_adapter.abs_work_path(LIBRARY_SLUG, LIBRARY_ROOT))
    if root.exists():
        for path in sorted(root.rglob("*.md")):
            meta, body = parse_block_file(path.read_text(encoding="utf-8"))
            block_id = meta.get("block_id")
            if not block_id:
                continue
            rel = path.relative_to(root)
            category = rel.parts[0] if len(rel.parts) > 1 else meta.get("type", "")
            row = db.query(ReusableBlock).filter_by(block_id=block_id).first()
            if row is None:
                row = ReusableBlock(block_id=block_id)
                db.add(row)
            row.title = meta.get("title", block_id)
            row.category = category
            row.version = str(meta.get("version", ""))
            row.status = meta.get("status", "draft")
            row.owner = meta.get("owner", "")
            row.tags = json.dumps(meta.get("tags", []) or [])
            row.body = body
            row.git_path = f"{LIBRARY_ROOT}/{rel.as_posix()}"
            row.scope = "shared-library-approved"
            row.derivation_type = None
            row.document_id = None
    db.flush()
    return (
        db.query(ReusableBlock)
        .filter(ReusableBlock.document_id.is_(None))
        .order_by(ReusableBlock.category, ReusableBlock.title)
        .all()
    )
