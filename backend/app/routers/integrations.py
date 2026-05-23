"""Integration document endpoints — declare, generate, edit, validate, link."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    DOC_TYPE_HLD,
    DOC_TYPE_INTEGRATION,
    ArchitectureIncrement,
    Document,
    DocumentIntegrationLink,
    Integration,
    ValidationResult,
)
from app.schemas import (
    ContractIn,
    ContractOut,
    DocumentOut,
    IntegrationCreate,
    IntegrationCreateMissingOut,
    IntegrationListItem,
    IntegrationOut,
    IntegrationUpdate,
    IntegrationValidationOut,
    LinkedIntegrationOut,
    ValidationItem,
)
from app.services import integration_types
from app.services.git_adapter import git_adapter
from app.services.integration_validation import validate_integration
from app.services.serializer import build_file_set
from app.services.template import apply_template
from app.utils import slugify
from app.views import (
    build_document_out,
    integration_list_item,
    integration_out,
    linked_integration_out,
)

router = APIRouter(tags=["integrations"])


# -- helpers --------------------------------------------------------------
def _get_integration(integration_id: int, db: Session) -> Integration:
    integration = db.get(Integration, integration_id)
    if integration is None:
        raise HTTPException(404, "Integration not found")
    return integration


def _repo_slug(integration: Integration) -> str:
    return integration.increment.application_group.repository.slug


def _commit_document(integration: Integration, message: str) -> None:
    """Write the integration document's canonical source to Git, if it exists."""
    if integration.document_id is None or integration.document is None:
        return
    git_adapter.commit(
        _repo_slug(integration), build_file_set(integration.document), message
    )


def _create_document(db: Session, integration: Integration) -> Document:
    """Instantiate the type's template as the integration document."""
    document = Document(
        increment_id=integration.increment_id,
        type=DOC_TYPE_INTEGRATION,
        title=integration.name,
    )
    db.add(document)
    db.flush()
    apply_template(db, document, integration_types.template_name(integration.type))
    db.flush()
    integration.document_id = document.id
    db.flush()
    return document


def _recompute_contract_path(integration: Integration) -> None:
    if not integration.contract_filename:
        integration.contract_path = ""
        return
    try:
        metadata = json.loads(integration.metadata_json or "{}")
    except (ValueError, TypeError):
        metadata = {}
    integration.contract_path = integration_types.contract_rel_path(
        integration.type, integration.contract_filename, metadata or {}
    )


# -- increment-scoped endpoints ------------------------------------------
@router.get(
    "/api/increments/{increment_id}/integration-docs",
    response_model=list[IntegrationListItem],
)
def list_integration_docs(increment_id: int, db: Session = Depends(get_db)):
    increment = db.get(ArchitectureIncrement, increment_id)
    if increment is None:
        raise HTTPException(404, "Increment not found")
    rows = (
        db.query(Integration)
        .filter_by(increment_id=increment_id)
        .order_by(Integration.created_at)
        .all()
    )
    return [integration_list_item(r) for r in rows]


@router.post(
    "/api/increments/{increment_id}/integration-docs",
    response_model=IntegrationOut,
    status_code=201,
)
def create_integration_doc(
    increment_id: int, payload: IntegrationCreate, db: Session = Depends(get_db)
):
    increment = db.get(ArchitectureIncrement, increment_id)
    if increment is None:
        raise HTTPException(404, "Increment not found")
    if not integration_types.is_valid_type(payload.type):
        raise HTTPException(400, f"Unsupported integration type: {payload.type}")

    slug = slugify(payload.integration_id or payload.name)
    if (
        db.query(Integration)
        .filter_by(increment_id=increment_id, integration_id=slug)
        .first()
    ):
        raise HTTPException(409, f"Integration '{slug}' already exists")

    integration = Integration(
        increment_id=increment_id,
        integration_id=slug,
        name=payload.name,
        type=payload.type,
        source_application=payload.source_application,
        target_application=payload.target_application,
        required=payload.required,
        metadata_json="{}",
    )
    db.add(integration)
    db.flush()

    if payload.create_document:
        _create_document(db, integration)
        _commit_document(
            integration, f"Create {payload.type} integration '{integration.name}'"
        )
    db.commit()
    db.refresh(integration)
    return integration_out(integration, db)


@router.post(
    "/api/increments/{increment_id}/integration-docs/create-missing",
    response_model=IntegrationCreateMissingOut,
)
def create_missing_integration_docs(
    increment_id: int, db: Session = Depends(get_db)
):
    """Generate template documents for required integrations that lack one."""
    increment = db.get(ArchitectureIncrement, increment_id)
    if increment is None:
        raise HTTPException(404, "Increment not found")
    missing = (
        db.query(Integration)
        .filter_by(increment_id=increment_id, required=True, document_id=None)
        .all()
    )
    created: list[Integration] = []
    for integration in missing:
        _create_document(db, integration)
        _commit_document(
            integration,
            f"Create {integration.type} integration '{integration.name}'",
        )
        created.append(integration)
    db.commit()
    return IntegrationCreateMissingOut(
        created=[integration_list_item(i) for i in created]
    )


# -- integration-scoped endpoints ----------------------------------------
@router.get("/api/integrations/{integration_id}", response_model=IntegrationOut)
def get_integration(integration_id: int, db: Session = Depends(get_db)):
    return integration_out(_get_integration(integration_id, db), db)


@router.put("/api/integrations/{integration_id}", response_model=IntegrationOut)
def update_integration(
    integration_id: int, payload: IntegrationUpdate, db: Session = Depends(get_db)
):
    integration = _get_integration(integration_id, db)
    if payload.name is not None:
        integration.name = payload.name
        if integration.document is not None:
            integration.document.title = payload.name
    if payload.source_application is not None:
        integration.source_application = payload.source_application
    if payload.target_application is not None:
        integration.target_application = payload.target_application
    if payload.required is not None:
        integration.required = payload.required
    if payload.status is not None:
        integration.status = payload.status
    if payload.metadata is not None:
        integration.metadata_json = json.dumps(payload.metadata)
        _recompute_contract_path(integration)
    db.flush()
    _commit_document(integration, f"Update integration '{integration.name}'")
    db.commit()
    db.refresh(integration)
    return integration_out(integration, db)


@router.post(
    "/api/integrations/{integration_id}/document", response_model=IntegrationOut
)
def create_integration_document(
    integration_id: int, db: Session = Depends(get_db)
):
    """Generate the template document for a declared (document-less) integration."""
    integration = _get_integration(integration_id, db)
    if integration.document_id is not None:
        raise HTTPException(409, "Integration already has a document")
    _create_document(db, integration)
    _commit_document(
        integration, f"Create {integration.type} integration '{integration.name}'"
    )
    db.commit()
    db.refresh(integration)
    return integration_out(integration, db)


# -- contract -------------------------------------------------------------
@router.post(
    "/api/integrations/{integration_id}/contract", response_model=ContractOut
)
def set_contract(
    integration_id: int, payload: ContractIn, db: Session = Depends(get_db)
):
    integration = _get_integration(integration_id, db)
    integration.contract_filename = payload.filename
    integration.contract_content = payload.content
    _recompute_contract_path(integration)
    db.flush()
    _commit_document(
        integration, f"Update contract for integration '{integration.name}'"
    )
    db.commit()
    db.refresh(integration)
    return ContractOut(
        filename=integration.contract_filename,
        path=integration.contract_path,
        content=integration.contract_content,
    )


@router.get(
    "/api/integrations/{integration_id}/contract", response_model=ContractOut
)
def get_contract(integration_id: int, db: Session = Depends(get_db)):
    integration = _get_integration(integration_id, db)
    return ContractOut(
        filename=integration.contract_filename,
        path=integration.contract_path,
        content=integration.contract_content,
    )


# -- validation -----------------------------------------------------------
@router.post(
    "/api/integrations/{integration_id}/validate",
    response_model=IntegrationValidationOut,
)
def validate_integration_doc(integration_id: int, db: Session = Depends(get_db)):
    integration = _get_integration(integration_id, db)
    items = validate_integration(integration)
    if integration.document_id is not None:
        db.query(ValidationResult).filter_by(
            document_id=integration.document_id
        ).delete()
        for item in items:
            db.add(
                ValidationResult(
                    document_id=integration.document_id,
                    severity=item.severity,
                    message=item.message,
                )
            )
        db.commit()
    return IntegrationValidationOut(integration_id=integration.id, results=items)


@router.get(
    "/api/integrations/{integration_id}/validation",
    response_model=IntegrationValidationOut,
)
def get_integration_validation(
    integration_id: int, db: Session = Depends(get_db)
):
    integration = _get_integration(integration_id, db)
    if integration.document_id is None:
        return IntegrationValidationOut(
            integration_id=integration.id,
            results=[
                ValidationItem(
                    severity="info",
                    message="Integration has no document yet — create it first",
                )
            ],
        )
    rows = (
        db.query(ValidationResult)
        .filter_by(document_id=integration.document_id)
        .all()
    )
    return IntegrationValidationOut(
        integration_id=integration.id,
        results=[
            ValidationItem(severity=r.severity, message=r.message)
            for r in rows
        ],
    )


# -- HLD linked references ------------------------------------------------
@router.post(
    "/api/hlds/{document_id}/linked-references/integrations/{integration_id}",
    response_model=DocumentOut,
)
def link_integration_to_hld(
    document_id: int, integration_id: int, db: Session = Depends(get_db)
):
    document = db.get(Document, document_id)
    if document is None or document.type != DOC_TYPE_HLD:
        raise HTTPException(404, "HLD document not found")
    integration = _get_integration(integration_id, db)
    existing = (
        db.query(DocumentIntegrationLink)
        .filter_by(document_id=document_id, integration_id=integration_id)
        .first()
    )
    if existing is None:
        db.add(
            DocumentIntegrationLink(
                document_id=document_id, integration_id=integration_id
            )
        )
        db.commit()
    db.refresh(document)
    return build_document_out(document)


@router.delete(
    "/api/hlds/{document_id}/linked-references/integrations/{integration_id}",
    response_model=DocumentOut,
)
def unlink_integration_from_hld(
    document_id: int, integration_id: int, db: Session = Depends(get_db)
):
    document = db.get(Document, document_id)
    if document is None or document.type != DOC_TYPE_HLD:
        raise HTTPException(404, "HLD document not found")
    db.query(DocumentIntegrationLink).filter_by(
        document_id=document_id, integration_id=integration_id
    ).delete()
    db.commit()
    db.refresh(document)
    return build_document_out(document)


@router.get(
    "/api/hlds/{document_id}/linked-integrations",
    response_model=list[LinkedIntegrationOut],
)
def list_linked_integrations(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if document is None or document.type != DOC_TYPE_HLD:
        raise HTTPException(404, "HLD document not found")
    links = (
        db.query(DocumentIntegrationLink)
        .filter_by(document_id=document_id)
        .all()
    )
    out: list[LinkedIntegrationOut] = []
    for link in links:
        integration = db.get(Integration, link.integration_id)
        if integration is not None:
            out.append(linked_integration_out(integration))
    return out
