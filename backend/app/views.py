"""Shared response builders."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session, object_session

from app.models import (
    REUSE_FORKED,
    REUSE_SNAPSHOT,
    Document,
    DocumentIntegrationLink,
    DocumentReuseInstance,
    Integration,
    ReusableBlock,
)
from app.schemas import (
    DiagramOut,
    DocumentOut,
    IntegrationListItem,
    IntegrationOut,
    LinkedHldOut,
    LinkedIntegrationOut,
    MetadataFieldSpec,
    ReusableBlockOut,
    ReuseInstanceOut,
    SectionOut,
)
from app.services import integration_types
from app.services.numbering import ordered_children, ordered_roots


def _integration_metadata(integration: Integration) -> dict:
    try:
        data = json.loads(integration.metadata_json or "{}")
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _type_label(integration_type: str) -> str:
    return integration_types.INTEGRATION_TYPE_DEFS.get(
        integration_type, {}
    ).get("label", integration_type)


def integration_list_item(integration: Integration) -> IntegrationListItem:
    """Row schema for the increment integration-docs table."""
    return IntegrationListItem(
        id=integration.id,
        increment_id=integration.increment_id,
        integration_id=integration.integration_id,
        name=integration.name,
        type=integration.type,
        type_label=_type_label(integration.type),
        source_application=integration.source_application,
        target_application=integration.target_application,
        required=integration.required,
        status=integration.status,
        document_id=integration.document_id,
        document_filename=(
            "integration.md" if integration.document_id is not None else None
        ),
    )


def linked_integration_out(integration: Integration) -> LinkedIntegrationOut:
    return LinkedIntegrationOut(
        id=integration.id,
        integration_id=integration.integration_id,
        name=integration.name,
        type=integration.type,
        type_label=_type_label(integration.type),
        source_application=integration.source_application,
        target_application=integration.target_application,
        status=integration.status,
        document_id=integration.document_id,
    )


def integration_out(integration: Integration, db: Session) -> IntegrationOut:
    """Full integration detail incl. metadata schema and linked HLDs."""
    type_def = integration_types.INTEGRATION_TYPE_DEFS.get(integration.type, {})
    links = (
        db.query(DocumentIntegrationLink)
        .filter_by(integration_id=integration.id)
        .all()
    )
    linked_hlds: list[LinkedHldOut] = []
    for link in links:
        doc = db.get(Document, link.document_id)
        if doc is not None:
            linked_hlds.append(
                LinkedHldOut(document_id=doc.id, title=doc.title)
            )
    return IntegrationOut(
        id=integration.id,
        increment_id=integration.increment_id,
        integration_id=integration.integration_id,
        name=integration.name,
        type=integration.type,
        type_label=type_def.get("label", integration.type),
        source_application=integration.source_application,
        target_application=integration.target_application,
        required=integration.required,
        status=integration.status,
        document_id=integration.document_id,
        metadata=_integration_metadata(integration),
        metadata_schema=[
            MetadataFieldSpec(**f)
            for f in integration_types.metadata_schema(integration.type)
        ],
        contract_filename=integration.contract_filename,
        contract_path=integration.contract_path,
        has_contract=bool((integration.contract_content or "").strip()),
        contract_format=type_def.get("contract_format", ""),
        linked_hlds=linked_hlds,
    )


def block_out(block: ReusableBlock) -> ReusableBlockOut:
    """Convert a ``ReusableBlock`` row to its API schema (tags JSON → list)."""
    try:
        tags = json.loads(block.tags or "[]")
    except (ValueError, TypeError):
        tags = []
    return ReusableBlockOut(
        id=block.id,
        block_id=block.block_id,
        title=block.title,
        category=block.category,
        version=block.version,
        status=block.status,
        owner=block.owner,
        tags=tags if isinstance(tags, list) else [],
        body=block.body,
        scope=block.scope,
        derived_from=block.derived_from,
        derived_from_version=block.derived_from_version,
        derivation_type=block.derivation_type,
        document_id=block.document_id,
    )


def reuse_instance_out(
    instance: DocumentReuseInstance, blocks: dict[str, ReusableBlock]
) -> ReuseInstanceOut:
    """Resolve a reuse instance into a display-ready schema.

    ``blocks`` maps ``block_id`` → row for every reusable block (library + forks).
    """
    library = blocks.get(instance.block_id)
    fork = (
        blocks.get(instance.derived_block_id) if instance.derived_block_id else None
    )
    if instance.reuse_mode == REUSE_FORKED:
        title = (
            fork.title if fork else (instance.derived_block_id or instance.block_id)
        )
        body = fork.body if fork else ""
        broken = fork is None
    elif instance.reuse_mode == REUSE_SNAPSHOT:
        title = library.title if library else instance.block_id
        body = instance.snapshot_content
        broken = False
    else:  # linked
        title = library.title if library else instance.block_id
        body = library.body if library else ""
        broken = library is None
    return ReuseInstanceOut(
        id=instance.id,
        document_id=instance.document_id,
        section_id=instance.section_id,
        block_id=instance.block_id,
        reuse_mode=instance.reuse_mode,
        source_version=instance.source_version,
        derived_block_id=instance.derived_block_id,
        rationale=instance.rationale,
        status=instance.status,
        order_index=instance.order_index,
        title=title,
        body=body,
        library_version=library.version if library else None,
        library_status=library.status if library else None,
        broken=broken,
    )


def build_document_out(document: Document) -> DocumentOut:
    """Assemble the full editor payload for a document."""
    sections: list[SectionOut] = []
    for chapter in ordered_roots(document):
        sections.append(SectionOut.model_validate(chapter))
        for sub in ordered_children(document, chapter.id):
            sections.append(SectionOut.model_validate(sub))

    increment = document.increment
    group = increment.application_group
    repository = group.repository

    db = object_session(document)
    blocks: dict[str, ReusableBlock] = {}
    if db is not None:
        blocks = {b.block_id: b for b in db.query(ReusableBlock).all()}
    instances = sorted(
        document.reuse_instances, key=lambda i: (i.section_id, i.order_index)
    )

    linked_integrations: list[LinkedIntegrationOut] = []
    integration_ref: LinkedIntegrationOut | None = None
    if db is not None:
        links = (
            db.query(DocumentIntegrationLink)
            .filter_by(document_id=document.id)
            .all()
        )
        for link in links:
            integration = db.get(Integration, link.integration_id)
            if integration is not None:
                linked_integrations.append(linked_integration_out(integration))
        # Back-link: when *this* document is an integration doc, surface a
        # pointer to its Integration row so the editor can load it.
        owning = (
            db.query(Integration).filter_by(document_id=document.id).first()
        )
        if owning is not None:
            integration_ref = linked_integration_out(owning)

    return DocumentOut(
        id=document.id,
        increment_id=document.increment_id,
        type=document.type,
        title=document.title,
        git_branch=document.git_branch,
        head_commit=document.head_commit,
        sections=sections,
        diagrams=[DiagramOut.model_validate(d) for d in document.diagrams],
        reuse_instances=[reuse_instance_out(i, blocks) for i in instances],
        linked_integrations=linked_integrations,
        integration_ref=integration_ref,
        breadcrumb={
            "repository": repository.name,
            "application_group": group.name,
            "increment": increment.name,
            "document": document.title,
        },
    )
