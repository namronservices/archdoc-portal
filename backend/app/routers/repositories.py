"""Repository and application-group endpoints."""
from __future__ import annotations

import yaml
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ApplicationGroup, Repository
from app.schemas import (
    ApplicationGroupCreate,
    ApplicationGroupOut,
    RepositoryCreate,
    RepositoryOut,
)
from app.services.git_adapter import git_adapter
from app.utils import slugify

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


@router.post("", response_model=RepositoryOut, status_code=201)
def create_repository(payload: RepositoryCreate, db: Session = Depends(get_db)):
    slug = slugify(payload.slug or payload.name)
    if db.query(Repository).filter_by(slug=slug).first():
        raise HTTPException(409, f"Repository '{slug}' already exists")

    git_path = git_adapter.init_repository(slug)
    repo = Repository(slug=slug, name=payload.name, git_path=git_path)
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


@router.get("", response_model=list[RepositoryOut])
def list_repositories(db: Session = Depends(get_db)):
    return db.query(Repository).order_by(Repository.created_at).all()


@router.post(
    "/{repository_id}/application-groups",
    response_model=ApplicationGroupOut,
    status_code=201,
)
def create_application_group(
    repository_id: int,
    payload: ApplicationGroupCreate,
    db: Session = Depends(get_db),
):
    repo = db.get(Repository, repository_id)
    if repo is None:
        raise HTTPException(404, "Repository not found")

    slug = slugify(payload.slug or payload.name)
    existing = db.query(ApplicationGroup).filter_by(slug=slug).first()
    if existing is not None:
        if (
            existing.repository_id is not None
            and existing.repository_id != repository_id
        ):
            raise HTTPException(409, f"Application group '{slug}' already exists")
        # Adopt the enterprise-synced group into this repository.
        existing.repository_id = repository_id
        if not existing.description and payload.description:
            existing.description = payload.description
        if not existing.name and payload.name:
            existing.name = payload.name
        group = existing
    else:
        group = ApplicationGroup(
            repository_id=repository_id,
            slug=slug,
            name=payload.name,
            description=payload.description,
        )
        db.add(group)
    db.commit()
    db.refresh(group)

    yaml_doc = yaml.safe_dump(
        {"slug": slug, "name": group.name, "description": group.description},
        sort_keys=False,
        allow_unicode=True,
    )
    git_adapter.commit(
        repo.slug,
        {"application-group.yaml": yaml_doc},
        f"Add application group '{group.name}'",
    )
    return group


@router.get(
    "/{repository_id}/application-groups",
    response_model=list[ApplicationGroupOut],
)
def list_application_groups(repository_id: int, db: Session = Depends(get_db)):
    repo = db.get(Repository, repository_id)
    if repo is None:
        raise HTTPException(404, "Repository not found")
    return (
        db.query(ApplicationGroup)
        .filter_by(repository_id=repository_id)
        .order_by(ApplicationGroup.created_at)
        .all()
    )
