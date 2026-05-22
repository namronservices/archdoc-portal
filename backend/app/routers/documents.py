"""Document-level endpoints: save to Git, export, validation."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    KIND_TEMPLATE_REQUIRED,
    Document,
    ExportJob,
    ValidationResult,
)
from app.schemas import (
    CommitInfoOut,
    ExportJobOut,
    ExportRequest,
    ValidationItem,
    ValidationOut,
)
from app.services.export import run_export
from app.services.git_adapter import git_adapter
from app.services.serializer import build_file_set

router = APIRouter(tags=["documents"])


def _get_document(document_id: int, db: Session) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    return document


def _repo_slug(document: Document) -> str:
    return document.increment.application_group.repository.slug


@router.post("/api/documents/{document_id}/save", response_model=CommitInfoOut)
def save_document(document_id: int, db: Session = Depends(get_db)):
    """Write the canonical Markdown/YAML/Mermaid source to Git and commit."""
    document = _get_document(document_id, db)
    commit = git_adapter.commit(
        _repo_slug(document),
        build_file_set(document),
        f"Update HLD '{document.title}'",
    )
    document.head_commit = commit.short_hash
    db.commit()
    return CommitInfoOut(**commit.__dict__)


@router.post("/api/documents/{document_id}/export", response_model=ExportJobOut)
def export_document(
    document_id: int, payload: ExportRequest, db: Session = Depends(get_db)
):
    document = _get_document(document_id, db)
    job = ExportJob(document_id=document_id, format=payload.format, status="running")
    db.add(job)
    db.commit()
    db.refresh(job)

    result = run_export(document, payload.format)
    if result.ok:
        job.status = "completed"
        job.artifact_path = result.artifact_path
    else:
        job.status = "failed"
        job.error = result.error
    db.commit()
    db.refresh(job)
    return ExportJobOut.model_validate(job)


@router.get("/api/exports/{job_id}/download")
def download_export(job_id: int, db: Session = Depends(get_db)):
    job = db.get(ExportJob, job_id)
    if job is None or job.status != "completed" or not job.artifact_path:
        raise HTTPException(404, "Export artifact not available")
    if not os.path.exists(job.artifact_path):
        raise HTTPException(404, "Export artifact file is missing")
    return FileResponse(
        job.artifact_path, filename=os.path.basename(job.artifact_path)
    )


@router.get("/api/documents/{document_id}/validation", response_model=ValidationOut)
def validate_document(document_id: int, db: Session = Depends(get_db)):
    document = _get_document(document_id, db)
    items: list[ValidationItem] = []

    for section in document.sections:
        if section.kind == KIND_TEMPLATE_REQUIRED and not section.content.strip():
            items.append(
                ValidationItem(
                    severity="warning",
                    section_id=section.id,
                    message=f"Required section '{section.number} {section.title}' is empty",
                )
            )

    for diagram in document.diagrams:
        if diagram.render_status == "error":
            items.append(
                ValidationItem(
                    severity="error",
                    section_id=diagram.section_id,
                    message=f"Diagram '{diagram.name}' is invalid: {diagram.last_error}",
                )
            )
        elif diagram.render_status == "pending":
            items.append(
                ValidationItem(
                    severity="info",
                    section_id=diagram.section_id,
                    message=f"Diagram '{diagram.name}' has not been rendered yet",
                )
            )

    # Persist a snapshot of the latest validation run.
    db.query(ValidationResult).filter_by(document_id=document_id).delete()
    for item in items:
        db.add(
            ValidationResult(
                document_id=document_id,
                section_id=item.section_id,
                severity=item.severity,
                message=item.message,
            )
        )
    db.commit()

    return ValidationOut(document_id=document_id, results=items)
