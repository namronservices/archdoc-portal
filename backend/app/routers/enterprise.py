"""Enterprise repository endpoints — TOGAF objects + dashboard + start-increment.

The router is intentionally repetitive (one block per TOGAF type) so adding a
new type later requires only its own block; no clever factories to debug.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import yaml
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    DOC_TYPE_HLD,
    Application,
    ApplicationGroup,
    ApplicationLink,
    ArchitectureContextLink,
    ArchitectureIncrement,
    Capability,
    DataDomain,
    DataObject,
    Document,
    Domain,
    Principle,
    Standard,
    TechnologyPlatform,
)
from app.schemas import (
    ApplicationIn,
    ApplicationLinkIn,
    ApplicationLinkOut,
    ApplicationOut,
    CapabilityIn,
    CapabilityOut,
    DashboardApplication,
    DashboardApplicationGroup,
    DashboardCapability,
    DashboardDomain,
    DashboardIncrement,
    DashboardOut,
    DashboardRecentHld,
    DataDomainIn,
    DataDomainOut,
    DataObjectIn,
    DataObjectOut,
    DomainIn,
    DomainOut,
    EnterpriseApplicationGroupIn,
    EnterpriseSyncOut,
    PrincipleIn,
    PrincipleOut,
    StandardIn,
    StandardOut,
    StartIncrementOut,
    StartIncrementRequest,
    TechnologyPlatformIn,
    TechnologyPlatformOut,
)
from app.services import enterprise_library
from app.services.git_adapter import git_adapter
from app.services.repository_provisioner import ensure_repository_for_group
from app.services.serializer import build_file_set
from app.services.template import apply_hld_template, template_title
from app.utils import slugify

router = APIRouter(prefix="/api/enterprise", tags=["enterprise"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ensure_synced(db: Session) -> None:
    """Sync the enterprise repo into the DB the first time we serve a request."""
    if db.query(Domain).first() is None:
        enterprise_library.sync_enterprise(db)
        db.commit()


def _yaml_dump(meta: dict) -> str:
    return yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)


def _commit_object(rel_path: str, meta: dict, message: str) -> None:
    enterprise_library.write_object_yaml(rel_path, meta, message)


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------
@router.post("/sync", response_model=EnterpriseSyncOut)
def sync(db: Session = Depends(get_db)):
    counts = enterprise_library.sync_enterprise(db)
    db.commit()
    return EnterpriseSyncOut(counts=counts)


# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------
@router.get("/domains", response_model=list[DomainOut])
def list_domains(db: Session = Depends(get_db)):
    _ensure_synced(db)
    return db.query(Domain).order_by(Domain.name).all()


@router.post("/domains", response_model=DomainOut, status_code=201)
def create_domain(payload: DomainIn, db: Session = Depends(get_db)):
    _ensure_synced(db)
    slug = slugify(payload.slug or payload.name)
    if db.query(Domain).filter_by(slug=slug).first():
        raise HTTPException(409, f"Domain '{slug}' already exists")
    row = Domain(
        slug=slug,
        name=payload.name,
        owner=payload.owner,
        description=payload.description,
        archimate_type=payload.archimate_type,
        git_path=f"business/domains/{slug}.yaml",
    )
    db.add(row)
    db.flush()
    _commit_object(
        row.git_path,
        {
            "domain_id": slug,
            "name": row.name,
            "owner": row.owner,
            "archimate_type": row.archimate_type,
            "description": row.description,
        },
        f"Add domain '{row.name}'",
    )
    db.commit()
    return row


@router.get("/domains/{slug}", response_model=DomainOut)
def get_domain(slug: str, db: Session = Depends(get_db)):
    row = db.query(Domain).filter_by(slug=slug).first()
    if row is None:
        raise HTTPException(404, "Domain not found")
    return row


@router.put("/domains/{slug}", response_model=DomainOut)
def update_domain(slug: str, payload: DomainIn, db: Session = Depends(get_db)):
    row = db.query(Domain).filter_by(slug=slug).first()
    if row is None:
        raise HTTPException(404, "Domain not found")
    row.name = payload.name
    row.owner = payload.owner
    row.description = payload.description
    if payload.archimate_type is not None:
        row.archimate_type = payload.archimate_type
    db.flush()
    _commit_object(
        row.git_path or f"business/domains/{slug}.yaml",
        {
            "domain_id": slug,
            "name": row.name,
            "owner": row.owner,
            "archimate_type": row.archimate_type,
            "description": row.description,
        },
        f"Update domain '{row.name}'",
    )
    db.commit()
    return row


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------
@router.get("/capabilities", response_model=list[CapabilityOut])
def list_capabilities(
    domain_slug: str | None = None, db: Session = Depends(get_db)
):
    _ensure_synced(db)
    q = db.query(Capability)
    if domain_slug:
        q = q.filter_by(domain_slug=domain_slug)
    return q.order_by(Capability.name).all()


@router.post("/capabilities", response_model=CapabilityOut, status_code=201)
def create_capability(payload: CapabilityIn, db: Session = Depends(get_db)):
    _ensure_synced(db)
    slug = slugify(payload.slug or payload.name)
    if db.query(Capability).filter_by(slug=slug).first():
        raise HTTPException(409, f"Capability '{slug}' already exists")
    row = Capability(
        slug=slug,
        name=payload.name,
        domain_slug=payload.domain_slug,
        criticality=payload.criticality,
        description=payload.description,
        archimate_type=payload.archimate_type,
        git_path=f"business/capabilities/{slug}.yaml",
    )
    db.add(row)
    db.flush()
    _commit_object(
        row.git_path,
        {
            "capability_id": slug,
            "name": row.name,
            "domain_id": row.domain_slug,
            "criticality": row.criticality,
            "archimate_type": row.archimate_type,
            "description": row.description,
        },
        f"Add capability '{row.name}'",
    )
    db.commit()
    return row


@router.get("/capabilities/{slug}", response_model=CapabilityOut)
def get_capability(slug: str, db: Session = Depends(get_db)):
    row = db.query(Capability).filter_by(slug=slug).first()
    if row is None:
        raise HTTPException(404, "Capability not found")
    return row


@router.put("/capabilities/{slug}", response_model=CapabilityOut)
def update_capability(
    slug: str, payload: CapabilityIn, db: Session = Depends(get_db)
):
    row = db.query(Capability).filter_by(slug=slug).first()
    if row is None:
        raise HTTPException(404, "Capability not found")
    row.name = payload.name
    row.domain_slug = payload.domain_slug
    row.criticality = payload.criticality
    row.description = payload.description
    if payload.archimate_type is not None:
        row.archimate_type = payload.archimate_type
    db.flush()
    _commit_object(
        row.git_path or f"business/capabilities/{slug}.yaml",
        {
            "capability_id": slug,
            "name": row.name,
            "domain_id": row.domain_slug,
            "criticality": row.criticality,
            "archimate_type": row.archimate_type,
            "description": row.description,
        },
        f"Update capability '{row.name}'",
    )
    db.commit()
    return row


# ---------------------------------------------------------------------------
# Application groups (shared with the operational `application_groups` table)
# ---------------------------------------------------------------------------
def _ag_to_dict(group: ApplicationGroup) -> dict:
    return {
        "application_group_id": group.slug,
        "name": group.name,
        "domain_id": group.domain_slug,
        "archimate_type": group.archimate_type,
        "description": group.description,
    }


@router.get("/application-groups", response_model=list[dict])
def list_application_groups_enterprise(db: Session = Depends(get_db)):
    _ensure_synced(db)
    rows = db.query(ApplicationGroup).order_by(ApplicationGroup.name).all()
    return [_ag_to_dict(r) | {"id": r.id, "repository_id": r.repository_id} for r in rows]


@router.post("/application-groups", response_model=dict, status_code=201)
def create_application_group_enterprise(
    payload: EnterpriseApplicationGroupIn, db: Session = Depends(get_db)
):
    _ensure_synced(db)
    slug = slugify(payload.slug or payload.name)
    existing = db.query(ApplicationGroup).filter_by(slug=slug).first()
    if existing is not None:
        raise HTTPException(409, f"Application group '{slug}' already exists")
    row = ApplicationGroup(
        slug=slug,
        name=payload.name,
        description=payload.description,
        domain_slug=payload.domain_slug,
        archimate_type=payload.archimate_type,
        git_path=f"application/application-groups/{slug}.yaml",
    )
    db.add(row)
    db.flush()
    _commit_object(
        row.git_path,
        _ag_to_dict(row),
        f"Add application group '{row.name}'",
    )
    db.commit()
    return _ag_to_dict(row) | {"id": row.id, "repository_id": row.repository_id}


@router.get("/application-groups/{slug}", response_model=dict)
def get_application_group_enterprise(slug: str, db: Session = Depends(get_db)):
    row = db.query(ApplicationGroup).filter_by(slug=slug).first()
    if row is None:
        raise HTTPException(404, "Application group not found")
    return _ag_to_dict(row) | {"id": row.id, "repository_id": row.repository_id}


@router.put("/application-groups/{slug}", response_model=dict)
def update_application_group_enterprise(
    slug: str,
    payload: EnterpriseApplicationGroupIn,
    db: Session = Depends(get_db),
):
    row = db.query(ApplicationGroup).filter_by(slug=slug).first()
    if row is None:
        raise HTTPException(404, "Application group not found")
    row.name = payload.name
    row.description = payload.description
    row.domain_slug = payload.domain_slug
    if payload.archimate_type is not None:
        row.archimate_type = payload.archimate_type
    db.flush()
    _commit_object(
        row.git_path or f"application/application-groups/{slug}.yaml",
        _ag_to_dict(row),
        f"Update application group '{row.name}'",
    )
    db.commit()
    return _ag_to_dict(row) | {"id": row.id, "repository_id": row.repository_id}


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
def _app_to_dict(row: Application) -> dict:
    try:
        caps = json.loads(row.supports_capabilities or "[]")
    except (ValueError, TypeError):
        caps = []
    return {
        "slug": row.slug,
        "name": row.name,
        "application_group_slug": row.application_group_slug,
        "domain_slug": row.domain_slug,
        "type": row.type,
        "architecture_state": row.architecture_state,
        "lifecycle": row.lifecycle,
        "criticality": row.criticality,
        "owner": row.owner,
        "supports_capabilities": caps,
        "archimate_type": row.archimate_type,
        "git_path": row.git_path,
    }


@router.get("/applications", response_model=list[ApplicationOut])
def list_applications(
    domain_slug: str | None = None,
    application_group_slug: str | None = None,
    db: Session = Depends(get_db),
):
    _ensure_synced(db)
    q = db.query(Application)
    if domain_slug:
        q = q.filter_by(domain_slug=domain_slug)
    if application_group_slug:
        q = q.filter_by(application_group_slug=application_group_slug)
    return [_app_to_dict(r) for r in q.order_by(Application.name).all()]


@router.post("/applications", response_model=ApplicationOut, status_code=201)
def create_application(payload: ApplicationIn, db: Session = Depends(get_db)):
    _ensure_synced(db)
    slug = slugify(payload.slug or payload.name)
    if db.query(Application).filter_by(slug=slug).first():
        raise HTTPException(409, f"Application '{slug}' already exists")
    row = Application(
        slug=slug,
        name=payload.name,
        application_group_slug=payload.application_group_slug,
        domain_slug=payload.domain_slug,
        type=payload.type,
        architecture_state=payload.architecture_state,
        lifecycle=payload.lifecycle,
        criticality=payload.criticality,
        owner=payload.owner,
        supports_capabilities=json.dumps(payload.supports_capabilities or []),
        archimate_type=payload.archimate_type,
        git_path=f"application/applications/{slug}.yaml",
    )
    db.add(row)
    db.flush()
    _commit_object(
        row.git_path,
        {
            "application_id": slug,
            "name": row.name,
            "application_group_id": row.application_group_slug,
            "domain_id": row.domain_slug,
            "type": row.type,
            "architecture_state": row.architecture_state,
            "lifecycle": row.lifecycle,
            "criticality": row.criticality,
            "owner": row.owner,
            "supports_capabilities": payload.supports_capabilities,
            "archimate_type": row.archimate_type,
        },
        f"Add application '{row.name}'",
    )
    db.commit()
    return _app_to_dict(row)


@router.get("/applications/{slug}", response_model=ApplicationOut)
def get_application(slug: str, db: Session = Depends(get_db)):
    row = db.query(Application).filter_by(slug=slug).first()
    if row is None:
        raise HTTPException(404, "Application not found")
    return _app_to_dict(row)


@router.put("/applications/{slug}", response_model=ApplicationOut)
def update_application(
    slug: str, payload: ApplicationIn, db: Session = Depends(get_db)
):
    row = db.query(Application).filter_by(slug=slug).first()
    if row is None:
        raise HTTPException(404, "Application not found")
    row.name = payload.name
    row.application_group_slug = payload.application_group_slug
    row.domain_slug = payload.domain_slug
    row.type = payload.type
    row.architecture_state = payload.architecture_state
    row.lifecycle = payload.lifecycle
    row.criticality = payload.criticality
    row.owner = payload.owner
    row.supports_capabilities = json.dumps(payload.supports_capabilities or [])
    if payload.archimate_type is not None:
        row.archimate_type = payload.archimate_type
    db.flush()
    _commit_object(
        row.git_path or f"application/applications/{slug}.yaml",
        {
            "application_id": slug,
            "name": row.name,
            "application_group_id": row.application_group_slug,
            "domain_id": row.domain_slug,
            "type": row.type,
            "architecture_state": row.architecture_state,
            "lifecycle": row.lifecycle,
            "criticality": row.criticality,
            "owner": row.owner,
            "supports_capabilities": payload.supports_capabilities,
            "archimate_type": row.archimate_type,
        },
        f"Update application '{row.name}'",
    )
    db.commit()
    return _app_to_dict(row)


# ---------------------------------------------------------------------------
# Application links / Data objects / Data domains / Technology platforms /
# Standards / Principles  — same shape, condensed
# ---------------------------------------------------------------------------
@router.get("/application-links", response_model=list[ApplicationLinkOut])
def list_application_links(db: Session = Depends(get_db)):
    _ensure_synced(db)
    return db.query(ApplicationLink).order_by(ApplicationLink.slug).all()


@router.post(
    "/application-links", response_model=ApplicationLinkOut, status_code=201
)
def create_application_link(
    payload: ApplicationLinkIn, db: Session = Depends(get_db)
):
    _ensure_synced(db)
    slug = slugify(
        payload.slug or f"{payload.source_app_slug}-to-{payload.target_app_slug}"
    )
    if db.query(ApplicationLink).filter_by(slug=slug).first():
        raise HTTPException(409, f"Application link '{slug}' already exists")
    row = ApplicationLink(
        slug=slug,
        source_app_slug=payload.source_app_slug,
        target_app_slug=payload.target_app_slug,
        kind=payload.kind,
        archimate_type=payload.archimate_type,
        git_path=f"application/links/{slug}.yaml",
    )
    db.add(row)
    db.flush()
    _commit_object(
        row.git_path,
        {
            "link_id": slug,
            "source_app": row.source_app_slug,
            "target_app": row.target_app_slug,
            "kind": row.kind,
            "archimate_type": row.archimate_type,
        },
        f"Add application link '{slug}'",
    )
    db.commit()
    return row


@router.get("/data-objects", response_model=list[DataObjectOut])
def list_data_objects(db: Session = Depends(get_db)):
    _ensure_synced(db)
    return db.query(DataObject).order_by(DataObject.name).all()


@router.post("/data-objects", response_model=DataObjectOut, status_code=201)
def create_data_object(payload: DataObjectIn, db: Session = Depends(get_db)):
    _ensure_synced(db)
    slug = slugify(payload.slug or payload.name)
    if db.query(DataObject).filter_by(slug=slug).first():
        raise HTTPException(409, f"Data object '{slug}' already exists")
    row = DataObject(
        slug=slug,
        name=payload.name,
        domain_slug=payload.domain_slug,
        description=payload.description,
        archimate_type=payload.archimate_type,
        git_path=f"data/data-objects/{slug}.yaml",
    )
    db.add(row)
    db.flush()
    _commit_object(
        row.git_path,
        {
            "data_object_id": slug,
            "name": row.name,
            "domain_id": row.domain_slug,
            "archimate_type": row.archimate_type,
            "description": row.description,
        },
        f"Add data object '{row.name}'",
    )
    db.commit()
    return row


@router.get("/data-domains", response_model=list[DataDomainOut])
def list_data_domains(db: Session = Depends(get_db)):
    _ensure_synced(db)
    return db.query(DataDomain).order_by(DataDomain.name).all()


@router.post("/data-domains", response_model=DataDomainOut, status_code=201)
def create_data_domain(payload: DataDomainIn, db: Session = Depends(get_db)):
    _ensure_synced(db)
    slug = slugify(payload.slug or payload.name)
    if db.query(DataDomain).filter_by(slug=slug).first():
        raise HTTPException(409, f"Data domain '{slug}' already exists")
    row = DataDomain(
        slug=slug,
        name=payload.name,
        description=payload.description,
        archimate_type=payload.archimate_type,
        git_path=f"data/data-domains/{slug}.yaml",
    )
    db.add(row)
    db.flush()
    _commit_object(
        row.git_path,
        {
            "data_domain_id": slug,
            "name": row.name,
            "archimate_type": row.archimate_type,
            "description": row.description,
        },
        f"Add data domain '{row.name}'",
    )
    db.commit()
    return row


@router.get("/technology-platforms", response_model=list[TechnologyPlatformOut])
def list_technology_platforms(db: Session = Depends(get_db)):
    _ensure_synced(db)
    return db.query(TechnologyPlatform).order_by(TechnologyPlatform.name).all()


@router.post(
    "/technology-platforms",
    response_model=TechnologyPlatformOut,
    status_code=201,
)
def create_technology_platform(
    payload: TechnologyPlatformIn, db: Session = Depends(get_db)
):
    _ensure_synced(db)
    slug = slugify(payload.slug or payload.name)
    if db.query(TechnologyPlatform).filter_by(slug=slug).first():
        raise HTTPException(409, f"Technology platform '{slug}' already exists")
    row = TechnologyPlatform(
        slug=slug,
        name=payload.name,
        type=payload.type,
        owner=payload.owner,
        description=payload.description,
        archimate_type=payload.archimate_type,
        git_path=f"technology/platforms/{slug}.yaml",
    )
    db.add(row)
    db.flush()
    _commit_object(
        row.git_path,
        {
            "technology_platform_id": slug,
            "name": row.name,
            "type": row.type,
            "owner": row.owner,
            "archimate_type": row.archimate_type,
            "description": row.description,
        },
        f"Add technology platform '{row.name}'",
    )
    db.commit()
    return row


@router.get("/standards", response_model=list[StandardOut])
def list_standards(db: Session = Depends(get_db)):
    _ensure_synced(db)
    return db.query(Standard).order_by(Standard.title).all()


@router.post("/standards", response_model=StandardOut, status_code=201)
def create_standard(payload: StandardIn, db: Session = Depends(get_db)):
    _ensure_synced(db)
    slug = slugify(payload.slug or payload.title)
    if db.query(Standard).filter_by(slug=slug).first():
        raise HTTPException(409, f"Standard '{slug}' already exists")
    row = Standard(
        slug=slug,
        title=payload.title,
        body=payload.body,
        archimate_type=payload.archimate_type,
        git_path=f"motivation-governance/standards/{slug}.yaml",
    )
    db.add(row)
    db.flush()
    _commit_object(
        row.git_path,
        {
            "standard_id": slug,
            "title": row.title,
            "archimate_type": row.archimate_type,
            "body": row.body,
        },
        f"Add standard '{row.title}'",
    )
    db.commit()
    return row


@router.get("/principles", response_model=list[PrincipleOut])
def list_principles(db: Session = Depends(get_db)):
    _ensure_synced(db)
    return db.query(Principle).order_by(Principle.title).all()


@router.post("/principles", response_model=PrincipleOut, status_code=201)
def create_principle(payload: PrincipleIn, db: Session = Depends(get_db)):
    _ensure_synced(db)
    slug = slugify(payload.slug or payload.title)
    if db.query(Principle).filter_by(slug=slug).first():
        raise HTTPException(409, f"Principle '{slug}' already exists")
    row = Principle(
        slug=slug,
        title=payload.title,
        body=payload.body,
        archimate_type=payload.archimate_type,
        git_path=f"motivation-governance/principles/{slug}.yaml",
    )
    db.add(row)
    db.flush()
    _commit_object(
        row.git_path,
        {
            "principle_id": slug,
            "title": row.title,
            "archimate_type": row.archimate_type,
            "body": row.body,
        },
        f"Add principle '{row.title}'",
    )
    db.commit()
    return row


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    _ensure_synced(db)

    domains = db.query(Domain).order_by(Domain.name).all()
    capabilities = db.query(Capability).order_by(Capability.name).all()
    app_groups = db.query(ApplicationGroup).order_by(ApplicationGroup.name).all()
    applications = db.query(Application).order_by(Application.name).all()
    data_domains = db.query(DataDomain).order_by(DataDomain.name).all()
    data_objects = db.query(DataObject).order_by(DataObject.name).all()
    platforms = db.query(TechnologyPlatform).order_by(TechnologyPlatform.name).all()
    standards = db.query(Standard).order_by(Standard.title).all()
    principles = db.query(Principle).order_by(Principle.title).all()

    # Counts per domain.
    caps_by_domain: dict[str, int] = {}
    for c in capabilities:
        if c.domain_slug:
            caps_by_domain[c.domain_slug] = caps_by_domain.get(c.domain_slug, 0) + 1
    apps_by_domain: dict[str, int] = {}
    apps_by_group: dict[str, int] = {}
    for a in applications:
        if a.domain_slug:
            apps_by_domain[a.domain_slug] = apps_by_domain.get(a.domain_slug, 0) + 1
        if a.application_group_slug:
            apps_by_group[a.application_group_slug] = (
                apps_by_group.get(a.application_group_slug, 0) + 1
            )
    groups_by_domain: dict[str, int] = {}
    for g in app_groups:
        if g.domain_slug:
            groups_by_domain[g.domain_slug] = groups_by_domain.get(g.domain_slug, 0) + 1

    business_domains = [
        DashboardDomain(
            slug=d.slug,
            name=d.name,
            capability_count=caps_by_domain.get(d.slug, 0),
            application_group_count=groups_by_domain.get(d.slug, 0),
            application_count=apps_by_domain.get(d.slug, 0),
        )
        for d in domains
    ]
    business_capabilities = [
        DashboardCapability(
            slug=c.slug,
            name=c.name,
            domain_slug=c.domain_slug,
            criticality=c.criticality,
        )
        for c in capabilities
    ]

    # Application groups w/ counts + recent increments.
    group_cards: list[DashboardApplicationGroup] = []
    for g in app_groups:
        increments = (
            db.query(ArchitectureIncrement)
            .filter_by(application_group_id=g.id)
            .order_by(ArchitectureIncrement.created_at.desc())
            .all()
        )
        hld_count = 0
        recent: list[DashboardIncrement] = []
        for inc in increments[:5]:
            hld = (
                db.query(Document)
                .filter_by(increment_id=inc.id, type=DOC_TYPE_HLD)
                .first()
            )
            if hld is not None:
                hld_count += 1
            recent.append(
                DashboardIncrement(
                    id=inc.id,
                    slug=inc.slug,
                    name=inc.name,
                    status=inc.status,
                    hld_id=hld.id if hld else None,
                )
            )
        # Count HLDs across all increments (not only recent).
        full_hld_count = (
            db.query(Document)
            .join(ArchitectureIncrement, Document.increment_id == ArchitectureIncrement.id)
            .filter(
                ArchitectureIncrement.application_group_id == g.id,
                Document.type == DOC_TYPE_HLD,
            )
            .count()
        )
        group_cards.append(
            DashboardApplicationGroup(
                id=g.id,
                slug=g.slug,
                name=g.name,
                domain_slug=g.domain_slug,
                increment_count=len(increments),
                hld_count=full_hld_count,
                application_count=apps_by_group.get(g.slug, 0),
                recent_increments=recent,
            )
        )

    application_cards = [
        DashboardApplication(
            slug=a.slug,
            name=a.name,
            application_group_slug=a.application_group_slug,
            domain_slug=a.domain_slug,
            architecture_state=a.architecture_state,
            criticality=a.criticality,
        )
        for a in applications
    ]

    # Recent HLDs (any group), most-recently updated first.
    recent_hld_rows = (
        db.query(Document)
        .filter(Document.type == DOC_TYPE_HLD)
        .order_by(Document.updated_at.desc())
        .limit(10)
        .all()
    )
    recent_hlds: list[DashboardRecentHld] = []
    for doc in recent_hld_rows:
        inc = doc.increment
        ag = inc.application_group if inc else None
        recent_hlds.append(
            DashboardRecentHld(
                id=doc.id,
                title=doc.title,
                increment_id=doc.increment_id,
                increment_slug=inc.slug if inc else "",
                application_group_slug=ag.slug if ag else None,
                updated_at=doc.updated_at,
            )
        )

    return DashboardOut(
        business={
            "domains": [d.model_dump() for d in business_domains],
            "capabilities": [c.model_dump() for c in business_capabilities],
        },
        data={
            "data_domains": [
                {"slug": d.slug, "name": d.name, "description": d.description}
                for d in data_domains
            ],
            "data_objects": [
                {
                    "slug": d.slug,
                    "name": d.name,
                    "domain_slug": d.domain_slug,
                    "description": d.description,
                }
                for d in data_objects
            ],
        },
        application={
            "application_groups": [g.model_dump() for g in group_cards],
            "applications": [a.model_dump() for a in application_cards],
        },
        technology={
            "platforms": [
                {
                    "slug": p.slug,
                    "name": p.name,
                    "type": p.type,
                    "owner": p.owner,
                }
                for p in platforms
            ],
        },
        motivation={
            "standards": [
                {"slug": s.slug, "title": s.title} for s in standards
            ],
            "principles": [
                {"slug": p.slug, "title": p.title} for p in principles
            ],
        },
        recent_hlds=recent_hlds,
    )


# ---------------------------------------------------------------------------
# Start increment (the dashboard "+ Start Increment" one-shot)
# ---------------------------------------------------------------------------
@router.post(
    "/application-groups/{group_slug}/start-increment",
    response_model=StartIncrementOut,
    status_code=201,
)
def start_increment(
    group_slug: str,
    payload: StartIncrementRequest,
    db: Session = Depends(get_db),
):
    _ensure_synced(db)
    group = db.query(ApplicationGroup).filter_by(slug=group_slug).first()
    if group is None:
        raise HTTPException(404, "Application group not found")

    repo = ensure_repository_for_group(db, group)

    # Increment: derive slug, prevent collision within the group.
    increment_slug = slugify(payload.increment_slug or payload.increment_name)
    if (
        db.query(ArchitectureIncrement)
        .filter_by(application_group_id=group.id, slug=increment_slug)
        .first()
    ):
        raise HTTPException(409, f"Increment '{increment_slug}' already exists")
    increment = ArchitectureIncrement(
        application_group_id=group.id,
        slug=increment_slug,
        name=payload.increment_name,
    )
    db.add(increment)
    db.flush()

    yaml_doc = yaml.safe_dump(
        {
            "slug": increment.slug,
            "name": increment.name,
            "status": increment.status,
        },
        sort_keys=False,
        allow_unicode=True,
    )
    git_adapter.commit(
        repo.slug,
        {f"increments/{increment.slug}/increment.yaml": yaml_doc},
        f"Add increment '{increment.name}'",
    )

    # HLD: template + Git serialization.
    document = Document(
        increment_id=increment.id,
        type=DOC_TYPE_HLD,
        title=payload.hld_title or f"{increment.name} — {template_title()}",
    )
    db.add(document)
    db.flush()
    apply_hld_template(db, document)
    db.flush()

    # Pre-link context — what we already know without asking the user.
    pre_links: list[tuple[str, str]] = [
        ("application_group", group.slug),
        ("architecture_increment", increment.slug),
    ]
    if group.domain_slug:
        pre_links.append(("domain", group.domain_slug))
    for object_type, object_slug in pre_links:
        db.add(
            ArchitectureContextLink(
                document_id=document.id,
                object_type=object_type,
                object_slug=object_slug,
            )
        )

    commit = git_adapter.commit(
        repo.slug,
        build_file_set(document),
        f"Create HLD for increment '{increment.name}'",
    )
    document.head_commit = commit.short_hash
    db.commit()

    return StartIncrementOut(
        application_group_slug=group.slug,
        increment_id=increment.id,
        hld_id=document.id,
    )
