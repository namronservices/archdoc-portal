"""Mermaid diagram endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Diagram, Document, DocumentSection
from app.schemas import DiagramCreate, DiagramOut, DiagramUpdate
from app.services import mermaid
from app.utils import slugify

router = APIRouter(tags=["diagrams"])


def _get_diagram(diagram_id: int, db: Session) -> Diagram:
    diagram = db.get(Diagram, diagram_id)
    if diagram is None:
        raise HTTPException(404, "Diagram not found")
    return diagram


@router.post("/api/hlds/{document_id}/diagrams", response_model=DiagramOut, status_code=201)
def create_diagram(
    document_id: int, payload: DiagramCreate, db: Session = Depends(get_db)
):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(404, "Document not found")
    if payload.section_id is not None:
        section = db.get(DocumentSection, payload.section_id)
        if section is None or section.document_id != document_id:
            raise HTTPException(404, "Section not found")

    diagram = Diagram(
        document_id=document_id,
        section_id=payload.section_id,
        name=slugify(payload.name),
        source=payload.source,
    )
    db.add(diagram)
    db.commit()
    db.refresh(diagram)
    return DiagramOut.model_validate(diagram)


@router.get("/api/diagrams/{diagram_id}", response_model=DiagramOut)
def get_diagram(diagram_id: int, db: Session = Depends(get_db)):
    return DiagramOut.model_validate(_get_diagram(diagram_id, db))


@router.put("/api/diagrams/{diagram_id}", response_model=DiagramOut)
def update_diagram(
    diagram_id: int, payload: DiagramUpdate, db: Session = Depends(get_db)
):
    diagram = _get_diagram(diagram_id, db)
    if payload.name is not None:
        diagram.name = slugify(payload.name)
    if payload.source is not None:
        diagram.source = payload.source
        diagram.render_status = "pending"
    if payload.section_id is not None:
        diagram.section_id = payload.section_id
    db.commit()
    db.refresh(diagram)
    return DiagramOut.model_validate(diagram)


@router.post("/api/diagrams/{diagram_id}/render", response_model=DiagramOut)
def render_diagram(diagram_id: int, db: Session = Depends(get_db)):
    diagram = _get_diagram(diagram_id, db)
    result = mermaid.render(diagram.source)
    if result.ok:
        diagram.svg = result.svg
        diagram.render_status = "rendered"
        diagram.last_error = ""
    else:
        diagram.svg = ""
        diagram.render_status = "error"
        diagram.last_error = result.error
    db.commit()
    db.refresh(diagram)
    return DiagramOut.model_validate(diagram)
