"""Auto-provision a Git Repository for an ApplicationGroup.

Phase 4 hides the Repository concept from users: when a UI flow (dashboard
``start-increment`` or enterprise admin app-group create) needs a project
repo and the group does not yet have one, we create it on demand and link
``ApplicationGroup.repository_id``.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ApplicationGroup, Repository
from app.services.git_adapter import git_adapter


def ensure_repository_for_group(
    db: Session, group: ApplicationGroup
) -> Repository:
    """Return the group's project repo, creating one if it has none yet."""
    if group.repository_id is not None:
        repo = db.get(Repository, group.repository_id)
        if repo is not None:
            return repo

    repo_slug = group.slug
    repo = db.query(Repository).filter_by(slug=repo_slug).first()
    if repo is None:
        bare_path = git_adapter.init_repository(repo_slug)
        repo = Repository(
            slug=repo_slug,
            name=group.name,
            git_path=bare_path,
        )
        db.add(repo)
        db.flush()

    group.repository_id = repo.id
    db.flush()
    return repo
