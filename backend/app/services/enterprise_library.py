"""Shared enterprise-repository: bootstrap, seed, sync TOGAF objects into DB.

The enterprise repository lives in its own Git repo (slug ``enterprise-repository``),
mirroring the ``architecture-library`` pattern used for reusable blocks. Each
TOGAF object type is a directory of YAML files; ``sync_enterprise`` mirrors them
into slug-keyed cache tables.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml
from sqlalchemy.orm import Session

from app.models import (
    Application,
    ApplicationGroup,
    ApplicationLink,
    Capability,
    DataDomain,
    DataObject,
    Domain,
    Principle,
    Standard,
    TechnologyPlatform,
)
from app.services.git_adapter import git_adapter

ENTERPRISE_SLUG = "enterprise-repository"
SEED_DIR = Path(__file__).resolve().parent.parent / "seed" / "enterprise"


@dataclass
class _TypeSpec:
    subdir: str
    id_keys: tuple[str, ...]
    upsert: Callable[[Session, dict, str], None]


def _str(value: object) -> str:
    return "" if value is None else str(value)


def _opt(value: object) -> str | None:
    return None if value is None else str(value)


def _slug(meta: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if meta.get(key):
            return str(meta[key])
    return None


# ---------------------------------------------------------------------------
# Per-type upserts. Each preserves operational columns we don't own (e.g.
# ApplicationGroup.repository_id, description) and only touches TOGAF columns.
# ---------------------------------------------------------------------------
def _upsert_domain(db: Session, meta: dict, git_path: str) -> None:
    slug = _slug(meta, ("domain_id", "slug"))
    if not slug:
        return
    row = db.query(Domain).filter_by(slug=slug).first() or Domain(slug=slug)
    row.name = _str(meta.get("name") or slug)
    row.owner = _str(meta.get("owner"))
    row.description = _str(meta.get("description"))
    row.archimate_type = _opt(meta.get("archimate_type"))
    row.git_path = git_path
    db.add(row)


def _upsert_capability(db: Session, meta: dict, git_path: str) -> None:
    slug = _slug(meta, ("capability_id", "slug"))
    if not slug:
        return
    row = (
        db.query(Capability).filter_by(slug=slug).first() or Capability(slug=slug)
    )
    row.name = _str(meta.get("name") or slug)
    row.domain_slug = _opt(meta.get("domain_id") or meta.get("domain_slug"))
    row.criticality = _opt(meta.get("criticality"))
    row.description = _str(meta.get("description"))
    row.archimate_type = _opt(meta.get("archimate_type"))
    row.git_path = git_path
    db.add(row)


def _upsert_application_group(db: Session, meta: dict, git_path: str) -> None:
    slug = _slug(meta, ("application_group_id", "slug"))
    if not slug:
        return
    row = (
        db.query(ApplicationGroup).filter_by(slug=slug).first()
        or ApplicationGroup(slug=slug, name=_str(meta.get("name") or slug))
    )
    # Don't clobber the operational name/description if a project flow set them.
    if meta.get("name"):
        row.name = str(meta["name"])
    if meta.get("description"):
        row.description = str(meta["description"])
    row.domain_slug = _opt(meta.get("domain_id") or meta.get("domain_slug"))
    row.archimate_type = _opt(meta.get("archimate_type"))
    row.git_path = git_path
    db.add(row)


def _upsert_application(db: Session, meta: dict, git_path: str) -> None:
    slug = _slug(meta, ("application_id", "slug"))
    if not slug:
        return
    row = (
        db.query(Application).filter_by(slug=slug).first() or Application(slug=slug)
    )
    row.name = _str(meta.get("name") or slug)
    row.application_group_slug = _opt(
        meta.get("application_group_id") or meta.get("application_group_slug")
    )
    row.domain_slug = _opt(meta.get("domain_id") or meta.get("domain_slug"))
    row.type = _opt(meta.get("type"))
    row.architecture_state = _opt(meta.get("architecture_state"))
    row.lifecycle = _opt(meta.get("lifecycle"))
    row.criticality = _opt(meta.get("criticality"))
    row.owner = _str(meta.get("owner"))
    row.supports_capabilities = json.dumps(
        meta.get("supports_capabilities") or []
    )
    row.archimate_type = _opt(meta.get("archimate_type"))
    row.git_path = git_path
    db.add(row)


def _upsert_application_link(db: Session, meta: dict, git_path: str) -> None:
    slug = _slug(meta, ("link_id", "slug"))
    if not slug:
        return
    row = (
        db.query(ApplicationLink).filter_by(slug=slug).first()
        or ApplicationLink(
            slug=slug,
            source_app_slug=_str(meta.get("source_app") or meta.get("source")),
            target_app_slug=_str(meta.get("target_app") or meta.get("target")),
        )
    )
    if meta.get("source_app") or meta.get("source"):
        row.source_app_slug = str(meta.get("source_app") or meta.get("source"))
    if meta.get("target_app") or meta.get("target"):
        row.target_app_slug = str(meta.get("target_app") or meta.get("target"))
    row.kind = _opt(meta.get("kind"))
    row.archimate_type = _opt(meta.get("archimate_type"))
    row.git_path = git_path
    db.add(row)


def _upsert_data_object(db: Session, meta: dict, git_path: str) -> None:
    slug = _slug(meta, ("data_object_id", "slug"))
    if not slug:
        return
    row = (
        db.query(DataObject).filter_by(slug=slug).first() or DataObject(slug=slug)
    )
    row.name = _str(meta.get("name") or slug)
    row.domain_slug = _opt(meta.get("domain_id") or meta.get("domain_slug"))
    row.description = _str(meta.get("description"))
    row.archimate_type = _opt(meta.get("archimate_type"))
    row.git_path = git_path
    db.add(row)


def _upsert_data_domain(db: Session, meta: dict, git_path: str) -> None:
    slug = _slug(meta, ("data_domain_id", "slug"))
    if not slug:
        return
    row = (
        db.query(DataDomain).filter_by(slug=slug).first() or DataDomain(slug=slug)
    )
    row.name = _str(meta.get("name") or slug)
    row.description = _str(meta.get("description"))
    row.archimate_type = _opt(meta.get("archimate_type"))
    row.git_path = git_path
    db.add(row)


def _upsert_technology_platform(db: Session, meta: dict, git_path: str) -> None:
    slug = _slug(meta, ("technology_platform_id", "platform_id", "slug"))
    if not slug:
        return
    row = (
        db.query(TechnologyPlatform).filter_by(slug=slug).first()
        or TechnologyPlatform(slug=slug)
    )
    row.name = _str(meta.get("name") or slug)
    row.type = _opt(meta.get("type"))
    row.owner = _str(meta.get("owner"))
    row.description = _str(meta.get("description"))
    row.archimate_type = _opt(meta.get("archimate_type"))
    row.git_path = git_path
    db.add(row)


def _upsert_standard(db: Session, meta: dict, git_path: str) -> None:
    slug = _slug(meta, ("standard_id", "slug"))
    if not slug:
        return
    row = db.query(Standard).filter_by(slug=slug).first() or Standard(slug=slug)
    row.title = _str(meta.get("title") or meta.get("name") or slug)
    row.body = _str(meta.get("body"))
    row.archimate_type = _opt(meta.get("archimate_type"))
    row.git_path = git_path
    db.add(row)


def _upsert_principle(db: Session, meta: dict, git_path: str) -> None:
    slug = _slug(meta, ("principle_id", "slug"))
    if not slug:
        return
    row = db.query(Principle).filter_by(slug=slug).first() or Principle(slug=slug)
    row.title = _str(meta.get("title") or meta.get("name") or slug)
    row.body = _str(meta.get("body"))
    row.archimate_type = _opt(meta.get("archimate_type"))
    row.git_path = git_path
    db.add(row)


TYPES: list[_TypeSpec] = [
    _TypeSpec("business/domains", ("domain_id", "slug"), _upsert_domain),
    _TypeSpec(
        "business/capabilities", ("capability_id", "slug"), _upsert_capability
    ),
    _TypeSpec(
        "application/application-groups",
        ("application_group_id", "slug"),
        _upsert_application_group,
    ),
    _TypeSpec(
        "application/applications",
        ("application_id", "slug"),
        _upsert_application,
    ),
    _TypeSpec(
        "application/links", ("link_id", "slug"), _upsert_application_link
    ),
    _TypeSpec("data/data-objects", ("data_object_id", "slug"), _upsert_data_object),
    _TypeSpec("data/data-domains", ("data_domain_id", "slug"), _upsert_data_domain),
    _TypeSpec(
        "technology/platforms",
        ("technology_platform_id", "platform_id", "slug"),
        _upsert_technology_platform,
    ),
    _TypeSpec(
        "motivation-governance/standards",
        ("standard_id", "slug"),
        _upsert_standard,
    ),
    _TypeSpec(
        "motivation-governance/principles",
        ("principle_id", "slug"),
        _upsert_principle,
    ),
]


def ensure_enterprise() -> None:
    """Create the enterprise repo and seed sample objects (idempotent)."""
    git_adapter.init_repository(ENTERPRISE_SLUG)
    if git_adapter.read_file(ENTERPRISE_SLUG, ".seeded") is not None:
        return
    files: dict[str, str] = {".seeded": "1\n"}
    if SEED_DIR.exists():
        for path in sorted(SEED_DIR.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(SEED_DIR).as_posix()
            files[rel] = path.read_text(encoding="utf-8")
    git_adapter.commit(ENTERPRISE_SLUG, files, "Seed enterprise repository")


def sync_enterprise(db: Session) -> dict[str, int]:
    """Walk the enterprise working tree and upsert every TOGAF object.

    Returns a per-type count of rows touched.
    """
    ensure_enterprise()
    root = Path(git_adapter.abs_work_path(ENTERPRISE_SLUG))
    counts: dict[str, int] = {}
    for spec in TYPES:
        type_dir = root / spec.subdir
        if not type_dir.exists():
            continue
        n = 0
        for path in sorted(type_dir.rglob("*.yaml")):
            try:
                meta = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                continue
            if not isinstance(meta, dict):
                continue
            rel = path.relative_to(root).as_posix()
            spec.upsert(db, meta, rel)
            n += 1
        counts[spec.subdir] = n
    db.flush()
    return counts


def write_object_yaml(
    rel_path: str, meta: dict, message: str
) -> None:
    """Persist a TOGAF object back to Git (called by enterprise router)."""
    ensure_enterprise()
    content = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    git_adapter.commit(ENTERPRISE_SLUG, {rel_path: content}, message)
