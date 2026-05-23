"""HLD document, section, chapter, and structure endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    CONTEXT_OBJECT_TYPES,
    DOC_TYPE_HLD,
    DOC_TYPE_INTEGRATION,
    KIND_CUSTOM,
    Application,
    ApplicationGroup,
    ArchitectureContextLink,
    ArchitectureIncrement,
    Capability,
    DataDomain,
    DataObject,
    Document,
    DocumentSection,
    Domain,
    Principle,
    Standard,
    TechnologyPlatform,
)
from app.schemas import (
    ArchitectureContextLayer,
    ArchitectureContextLinkOut,
    ArchitectureContextOut,
    ChapterCreate,
    ContextLinksUpdate,
    DocumentOut,
    HldCreate,
    SectionOut,
    SectionUpdate,
    StructureUpdate,
    SubchapterCreate,
)
from app.services.git_adapter import git_adapter
from app.services.numbering import renumber
from app.services.serializer import build_file_set
from app.services.template import apply_hld_template, template_title
from app.views import build_document_out

router = APIRouter(tags=["hld"])


def _get_hld(document_id: int, db: Session) -> Document:
    """Fetch an editable document — an HLD or an integration document.

    Both share the section/chapter/structure editing machinery.
    """
    document = db.get(Document, document_id)
    if document is None or document.type not in (
        DOC_TYPE_HLD,
        DOC_TYPE_INTEGRATION,
    ):
        raise HTTPException(404, "Document not found")
    return document


def _repo_slug(document: Document) -> str:
    return document.increment.application_group.repository.slug


@router.post(
    "/api/increments/{increment_id}/hld",
    response_model=DocumentOut,
    status_code=201,
)
def create_hld(
    increment_id: int, payload: HldCreate, db: Session = Depends(get_db)
):
    increment = db.get(ArchitectureIncrement, increment_id)
    if increment is None:
        raise HTTPException(404, "Increment not found")
    if db.query(Document).filter_by(increment_id=increment_id, type="hld").first():
        raise HTTPException(409, "This increment already has an HLD")

    document = Document(
        increment_id=increment_id,
        type="hld",
        title=payload.title or f"{increment.name} — {template_title()}",
    )
    db.add(document)
    db.flush()
    apply_hld_template(db, document)
    db.flush()

    # Pre-link any caller-supplied architecture-context references.
    for link in payload.context_links:
        if link.object_type not in CONTEXT_OBJECT_TYPES:
            continue
        db.add(
            ArchitectureContextLink(
                document_id=document.id,
                object_type=link.object_type,
                object_slug=link.object_slug,
            )
        )
    db.flush()

    commit = git_adapter.commit(
        _repo_slug(document),
        build_file_set(document),
        f"Create HLD for increment '{increment.name}'",
    )
    document.head_commit = commit.short_hash
    db.commit()
    db.refresh(document)
    return build_document_out(document)


@router.get("/api/hlds/{document_id}", response_model=DocumentOut)
def get_hld(document_id: int, db: Session = Depends(get_db)):
    return build_document_out(_get_hld(document_id, db))


@router.get("/api/increments/{increment_id}/hld", response_model=DocumentOut)
def get_increment_hld(increment_id: int, db: Session = Depends(get_db)):
    """Fetch the increment's HLD, if one exists."""
    document = (
        db.query(Document).filter_by(increment_id=increment_id, type=DOC_TYPE_HLD).first()
    )
    if document is None:
        raise HTTPException(404, "HLD not found for this increment")
    return build_document_out(document)


@router.put(
    "/api/hlds/{document_id}/sections/{section_id}", response_model=SectionOut
)
def update_section(
    document_id: int,
    section_id: int,
    payload: SectionUpdate,
    db: Session = Depends(get_db),
):
    _get_hld(document_id, db)
    section = db.get(DocumentSection, section_id)
    if section is None or section.document_id != document_id:
        raise HTTPException(404, "Section not found")
    if payload.title is not None:
        section.title = payload.title
    if payload.content is not None:
        section.content = payload.content
    db.commit()
    db.refresh(section)
    return SectionOut.model_validate(section)


@router.post("/api/hlds/{document_id}/chapters", response_model=DocumentOut)
def add_chapter(
    document_id: int, payload: ChapterCreate, db: Session = Depends(get_db)
):
    document = _get_hld(document_id, db)
    roots = [s for s in document.sections if s.parent_id is None]
    chapter = DocumentSection(
        document=document,
        parent_id=None,
        order_index=len(roots),
        title=payload.title,
        content=payload.content,
        kind=KIND_CUSTOM,
    )
    db.add(chapter)
    db.flush()
    renumber(db, document)
    db.commit()
    db.refresh(document)
    return build_document_out(document)


@router.post("/api/hlds/{document_id}/subchapters", response_model=DocumentOut)
def add_subchapter(
    document_id: int, payload: SubchapterCreate, db: Session = Depends(get_db)
):
    document = _get_hld(document_id, db)
    parent = db.get(DocumentSection, payload.parent_id)
    if parent is None or parent.document_id != document_id:
        raise HTTPException(404, "Parent chapter not found")
    if parent.parent_id is not None:
        raise HTTPException(400, "Sub-chapters can only be added to chapters")
    siblings = [s for s in document.sections if s.parent_id == parent.id]
    sub = DocumentSection(
        document=document,
        parent_id=parent.id,
        order_index=len(siblings),
        title=payload.title,
        content=payload.content,
        kind=KIND_CUSTOM,
    )
    db.add(sub)
    db.flush()
    renumber(db, document)
    db.commit()
    db.refresh(document)
    return build_document_out(document)


@router.put("/api/hlds/{document_id}/structure", response_model=DocumentOut)
def update_structure(
    document_id: int, payload: StructureUpdate, db: Session = Depends(get_db)
):
    document = _get_hld(document_id, db)
    by_id = {s.id: s for s in document.sections}
    for item in payload.items:
        section = by_id.get(item.id)
        if section is None:
            raise HTTPException(404, f"Section {item.id} not found")
        section.parent_id = item.parent_id
        section.order_index = item.order_index
    db.flush()
    renumber(db, document)
    db.commit()
    db.refresh(document)
    return build_document_out(document)


# ---------------------------------------------------------------------------
# Architecture context (Phase 4)
# ---------------------------------------------------------------------------
def _resolve_label(db: Session, object_type: str, object_slug: str) -> str | None:
    """Return the display name/title for a linked enterprise object, if any."""
    if object_type == "domain":
        row = db.query(Domain).filter_by(slug=object_slug).first()
        return row.name if row else None
    if object_type == "capability":
        row = db.query(Capability).filter_by(slug=object_slug).first()
        return row.name if row else None
    if object_type == "application_group":
        row = db.query(ApplicationGroup).filter_by(slug=object_slug).first()
        return row.name if row else None
    if object_type == "application":
        row = db.query(Application).filter_by(slug=object_slug).first()
        return row.name if row else None
    if object_type == "data_object":
        row = db.query(DataObject).filter_by(slug=object_slug).first()
        return row.name if row else None
    if object_type == "data_domain":
        row = db.query(DataDomain).filter_by(slug=object_slug).first()
        return row.name if row else None
    if object_type == "technology_platform":
        row = db.query(TechnologyPlatform).filter_by(slug=object_slug).first()
        return row.name if row else None
    if object_type == "standard":
        row = db.query(Standard).filter_by(slug=object_slug).first()
        return row.title if row else None
    if object_type == "principle":
        row = db.query(Principle).filter_by(slug=object_slug).first()
        return row.title if row else None
    if object_type == "architecture_increment":
        row = db.query(ArchitectureIncrement).filter_by(slug=object_slug).first()
        return row.name if row else None
    return None


# Per-layer ordering of object types — drives the Context tab grouping.
_LAYERS: list[tuple[str, list[str]]] = [
    ("Business Layer", ["domain", "capability"]),
    ("Solution Layer", ["application_group", "architecture_increment"]),
    ("Scope", ["application", "data_object", "data_domain"]),
    ("Technology Layer", ["technology_platform"]),
    ("Standards & Principles", ["standard", "principle"]),
]


def _build_chain(
    db: Session, document: Document, links_by_type: dict[str, list[ArchitectureContextLink]]
) -> list[ArchitectureContextLinkOut]:
    """Top-level connection chain: Enterprise → Domain → Capability → AppGroup
    → Increment → HLD."""
    chain: list[ArchitectureContextLinkOut] = []
    for object_type in (
        "domain",
        "capability",
        "application_group",
        "architecture_increment",
    ):
        link = next(iter(links_by_type.get(object_type, [])), None)
        if link is None:
            continue
        chain.append(
            ArchitectureContextLinkOut(
                object_type=object_type,
                object_slug=link.object_slug,
                label=_resolve_label(db, object_type, link.object_slug),
            )
        )
    chain.append(
        ArchitectureContextLinkOut(
            object_type="hld",
            object_slug=str(document.id),
            label=document.title,
        )
    )
    return chain


@router.get(
    "/api/hlds/{document_id}/architecture-context",
    response_model=ArchitectureContextOut,
)
def get_architecture_context(document_id: int, db: Session = Depends(get_db)):
    document = _get_hld(document_id, db)
    links = (
        db.query(ArchitectureContextLink)
        .filter_by(document_id=document.id)
        .order_by(ArchitectureContextLink.id)
        .all()
    )
    links_by_type: dict[str, list[ArchitectureContextLink]] = {}
    for link in links:
        links_by_type.setdefault(link.object_type, []).append(link)

    layers: list[ArchitectureContextLayer] = []
    for layer_name, types in _LAYERS:
        rows: list[ArchitectureContextLinkOut] = []
        for object_type in types:
            for link in links_by_type.get(object_type, []):
                rows.append(
                    ArchitectureContextLinkOut(
                        object_type=object_type,
                        object_slug=link.object_slug,
                        label=_resolve_label(db, object_type, link.object_slug),
                    )
                )
        layers.append(ArchitectureContextLayer(layer=layer_name, rows=rows))

    return ArchitectureContextOut(
        document_id=document.id,
        chain=_build_chain(db, document, links_by_type),
        layers=layers,
    )


@router.put(
    "/api/hlds/{document_id}/architecture-context",
    response_model=ArchitectureContextOut,
)
def replace_architecture_context(
    document_id: int,
    payload: ContextLinksUpdate,
    db: Session = Depends(get_db),
):
    document = _get_hld(document_id, db)
    db.query(ArchitectureContextLink).filter_by(document_id=document.id).delete()
    for link in payload.links:
        if link.object_type not in CONTEXT_OBJECT_TYPES:
            raise HTTPException(400, f"Unknown object_type '{link.object_type}'")
        db.add(
            ArchitectureContextLink(
                document_id=document.id,
                object_type=link.object_type,
                object_slug=link.object_slug,
            )
        )
    db.commit()
    return get_architecture_context(document_id, db)


@router.post(
    "/api/hlds/{document_id}/links/{object_type}/{object_slug}",
    response_model=ArchitectureContextOut,
)
def add_context_link(
    document_id: int,
    object_type: str,
    object_slug: str,
    db: Session = Depends(get_db),
):
    document = _get_hld(document_id, db)
    if object_type not in CONTEXT_OBJECT_TYPES:
        raise HTTPException(400, f"Unknown object_type '{object_type}'")
    existing = (
        db.query(ArchitectureContextLink)
        .filter_by(
            document_id=document.id,
            object_type=object_type,
            object_slug=object_slug,
        )
        .first()
    )
    if existing is None:
        db.add(
            ArchitectureContextLink(
                document_id=document.id,
                object_type=object_type,
                object_slug=object_slug,
            )
        )
        db.commit()
    return get_architecture_context(document_id, db)


@router.delete(
    "/api/hlds/{document_id}/links/{object_type}/{object_slug}",
    response_model=ArchitectureContextOut,
)
def remove_context_link(
    document_id: int,
    object_type: str,
    object_slug: str,
    db: Session = Depends(get_db),
):
    _get_hld(document_id, db)
    db.query(ArchitectureContextLink).filter_by(
        document_id=document_id,
        object_type=object_type,
        object_slug=object_slug,
    ).delete()
    db.commit()
    return get_architecture_context(document_id, db)
