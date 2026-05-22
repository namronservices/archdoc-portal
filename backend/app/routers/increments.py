"""Architecture increment endpoints."""
from __future__ import annotations

import yaml
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ApplicationGroup, ArchitectureIncrement
from app.schemas import IncrementCreate, IncrementOut
from app.services.git_adapter import git_adapter
from app.utils import slugify

router = APIRouter(prefix="/api/increments", tags=["increments"])


@router.post("", response_model=IncrementOut, status_code=201)
def create_increment(payload: IncrementCreate, db: Session = Depends(get_db)):
    group = db.get(ApplicationGroup, payload.application_group_id)
    if group is None:
        raise HTTPException(404, "Application group not found")

    slug = slugify(payload.slug or payload.name)
    exists = (
        db.query(ArchitectureIncrement)
        .filter_by(application_group_id=group.id, slug=slug)
        .first()
    )
    if exists:
        raise HTTPException(409, f"Increment '{slug}' already exists")

    increment = ArchitectureIncrement(
        application_group_id=group.id, slug=slug, name=payload.name
    )
    db.add(increment)
    db.commit()
    db.refresh(increment)

    yaml_doc = yaml.safe_dump(
        {"slug": slug, "name": increment.name, "status": increment.status},
        sort_keys=False,
        allow_unicode=True,
    )
    git_adapter.commit(
        group.repository.slug,
        {f"increments/{slug}/increment.yaml": yaml_doc},
        f"Add increment '{increment.name}'",
    )
    return increment


@router.get("/{increment_id}", response_model=IncrementOut)
def get_increment(increment_id: int, db: Session = Depends(get_db)):
    increment = db.get(ArchitectureIncrement, increment_id)
    if increment is None:
        raise HTTPException(404, "Increment not found")
    return increment
