"""Document export — assembles Markdown, renders diagrams, runs Pandoc."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import object_session

from app.config import settings
from app.models import (
    REUSE_FORKED,
    Application,
    ArchitectureContextLink,
    Capability,
    DataDomain,
    DataObject,
    Document,
    Domain,
    Principle,
    Standard,
    TechnologyPlatform,
)
from app.services.mermaid import mmdc_command
from app.services.serializer import build_markdown


_LABEL_RESOLVERS = {
    "domain": (Domain, "name"),
    "capability": (Capability, "name"),
    "application": (Application, "name"),
    "data_object": (DataObject, "name"),
    "data_domain": (DataDomain, "name"),
    "technology_platform": (TechnologyPlatform, "name"),
    "standard": (Standard, "title"),
    "principle": (Principle, "title"),
}


def _architecture_context(document: Document) -> dict:
    """Resolved architecture context for the export companion metadata."""
    db = object_session(document)
    if db is None:
        return {}
    links = (
        db.query(ArchitectureContextLink)
        .filter_by(document_id=document.id)
        .all()
    )
    rows: list[dict] = []
    for link in links:
        resolver = _LABEL_RESOLVERS.get(link.object_type)
        label = None
        if resolver is not None:
            model, attr = resolver
            row = db.query(model).filter_by(slug=link.object_slug).first()
            if row is not None:
                label = getattr(row, attr)
        rows.append(
            {
                "object_type": link.object_type,
                "object_slug": link.object_slug,
                "label": label,
            }
        )
    # Lightweight chain trail (Domain → Capability → AppGroup → Increment → HLD).
    chain: list[dict] = []
    by_type = {row["object_type"]: row for row in rows}
    for object_type in (
        "domain",
        "capability",
        "application_group",
        "architecture_increment",
    ):
        if object_type in by_type:
            chain.append(by_type[object_type])
    chain.append(
        {
            "object_type": "hld",
            "object_slug": str(document.id),
            "label": document.title,
        }
    )
    return {"chain": chain, "links": rows}


def _included_reusable_blocks(document: Document) -> list[dict]:
    """Export metadata: every reusable block resolved into the document."""
    out: list[dict] = []
    for r in document.reuse_instances:
        if r.reuse_mode == REUSE_FORKED and r.derived_block_id:
            out.append(
                {
                    "block_id": r.derived_block_id,
                    "mode": "forked",
                    "derived_from": r.block_id,
                }
            )
        else:
            out.append(
                {
                    "block_id": r.block_id,
                    "mode": r.reuse_mode,
                    "version": r.source_version,
                }
            )
    return out

SUPPORTED_FORMATS = ("docx", "pdf")


@dataclass
class ExportResult:
    ok: bool
    artifact_path: str = ""
    error: str = ""


def _render_diagrams_png(document: Document, diagrams_dir: Path) -> list[str]:
    """Render each diagram to PNG for embedding. Returns non-fatal warnings."""
    warnings: list[str] = []
    diagrams_dir.mkdir(parents=True, exist_ok=True)
    for diagram in document.diagrams:
        mmd = diagrams_dir / f"{diagram.name}.mmd"
        png = diagrams_dir / f"{diagram.name}.png"
        mmd.write_text(diagram.source or "", encoding="utf-8")
        if not (diagram.source or "").strip():
            warnings.append(f"Diagram '{diagram.name}' has no source")
            continue
        proc = subprocess.run(
            mmdc_command(str(mmd), str(png), "white"),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or not png.exists():
            warnings.append(f"Diagram '{diagram.name}' failed to render")
    return warnings


def run_export(document: Document, fmt: str) -> ExportResult:
    """Export ``document`` to ``fmt`` (docx|pdf); returns the stored artifact path."""
    if fmt not in SUPPORTED_FORMATS:
        return ExportResult(ok=False, error=f"Unsupported format: {fmt}")
    if shutil.which("pandoc") is None:
        return ExportResult(ok=False, error="pandoc is not installed")

    # Markdown references diagrams/<name>.svg; use PNG for portable export embedding.
    # resolve=True expands linked reuse directives to their library content.
    markdown = build_markdown(document, resolve=True).replace(".svg)", ".png)")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "hld.md").write_text(markdown, encoding="utf-8")
        _render_diagrams_png(document, tmp_path / "diagrams")

        out_dir = Path(settings.artifacts_root) / str(document.id)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        artifact = out_dir / f"hld-{stamp}.{fmt}"

        cmd = ["pandoc", "hld.md", "-o", str(artifact), "--toc", "--standalone"]
        if fmt == "pdf":
            cmd += ["--pdf-engine=weasyprint"]

        proc = subprocess.run(
            cmd, cwd=tmp_path, capture_output=True, text=True
        )
        if proc.returncode != 0 or not artifact.exists():
            return ExportResult(
                ok=False,
                error=(proc.stderr or proc.stdout or "Pandoc export failed").strip(),
            )

        # Companion metadata listing every resolved reusable block.
        meta_path = out_dir / f"{artifact.stem}.metadata.json"
        meta_path.write_text(
            json.dumps(
                {
                    "included_reusable_blocks": _included_reusable_blocks(document),
                    "architecture_context": _architecture_context(document),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return ExportResult(ok=True, artifact_path=str(artifact))
