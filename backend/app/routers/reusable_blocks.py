"""Reusable block library endpoints — browse, fetch, promote, compare."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ReusableBlock
from app.schemas import BlockCompareOut, ReusableBlockOut
from app.services.block_library import LIBRARY_SLUG, ensure_library, sync_library
from app.services.block_parser import render_block_file
from app.services.git_adapter import git_adapter
from app.views import block_out

router = APIRouter(tags=["reusable-blocks"])


@router.get("/api/reusable-blocks", response_model=list[ReusableBlockOut])
def list_reusable_blocks(
    category: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    """List library blocks, syncing the shared architecture-library repo first."""
    blocks = sync_library(db)
    db.commit()
    if category:
        blocks = [b for b in blocks if b.category == category]
    if q:
        needle = q.lower()
        blocks = [
            b
            for b in blocks
            if needle in b.title.lower()
            or needle in b.block_id.lower()
            or needle in (b.tags or "").lower()
        ]
    return [block_out(b) for b in blocks]


@router.get("/api/reusable-blocks/{block_id}", response_model=ReusableBlockOut)
def get_reusable_block(block_id: str, db: Session = Depends(get_db)):
    block = db.query(ReusableBlock).filter_by(block_id=block_id).first()
    if block is None:
        raise HTTPException(404, "Reusable block not found")
    return block_out(block)


@router.post(
    "/api/reusable-blocks/{block_id}/promote", response_model=ReusableBlockOut
)
def promote_block(block_id: str, db: Session = Depends(get_db)):
    """Promote a local fork into the shared library as a candidate block."""
    fork = db.query(ReusableBlock).filter_by(block_id=block_id).first()
    if fork is None or fork.derivation_type != "fork":
        raise HTTPException(404, "Forked block not found")
    ensure_library()
    category = fork.category or "forks"
    rel = f"reusable-blocks/{category}/{block_id}.md"
    meta = {
        "block_id": block_id,
        "title": fork.title,
        "type": category,
        "version": fork.version or "0.1",
        "status": "candidate",
        "owner": fork.owner or "solution-architecture",
        "derived_from": fork.derived_from,
        "derived_from_version": fork.derived_from_version,
        "derivation_type": "fork",
    }
    git_adapter.commit(
        LIBRARY_SLUG,
        {rel: render_block_file(meta, fork.body)},
        f"Promote forked block '{block_id}'",
    )
    fork.scope = "shared-library-candidate"
    fork.git_path = rel
    db.commit()
    db.refresh(fork)
    return block_out(fork)


@router.get(
    "/api/reusable-blocks/{block_id}/compare/{derived_block_id}",
    response_model=BlockCompareOut,
)
def compare_blocks(
    block_id: str, derived_block_id: str, db: Session = Depends(get_db)
):
    """Return the source block and a derived block side by side for diffing."""
    source = db.query(ReusableBlock).filter_by(block_id=block_id).first()
    derived = db.query(ReusableBlock).filter_by(block_id=derived_block_id).first()
    return BlockCompareOut(
        source=block_out(source) if source else None,
        derived=block_out(derived) if derived else None,
    )
