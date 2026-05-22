"""Document export — assembles Markdown, renders diagrams, runs Pandoc."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.models import Document
from app.services.mermaid import mmdc_command
from app.services.serializer import build_markdown

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
    markdown = build_markdown(document).replace(".svg)", ".png)")

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
        return ExportResult(ok=True, artifact_path=str(artifact))
