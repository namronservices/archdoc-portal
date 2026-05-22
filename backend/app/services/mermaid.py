"""Mermaid rendering — wraps the ``mmdc`` (mermaid-cli) binary."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.config import settings


@dataclass
class RenderResult:
    ok: bool
    svg: str = ""
    error: str = ""


def _mmdc_available() -> bool:
    return shutil.which("mmdc") is not None


def mmdc_command(in_path: str, out_path: str, background: str) -> list[str]:
    """Build an ``mmdc`` invocation, including the Puppeteer config when present."""
    cmd = ["mmdc", "-i", in_path, "-o", out_path, "-b", background]
    config = settings.mermaid_puppeteer_config
    if config and os.path.exists(config):
        cmd += ["-p", config]
    return cmd


def render(source: str) -> RenderResult:
    """Render Mermaid ``source`` to an SVG string.

    Returns ``ok=False`` with an ``error`` message when the source is invalid
    or the renderer is unavailable.
    """
    if not source.strip():
        return RenderResult(ok=False, error="Diagram source is empty")
    if not _mmdc_available():
        return RenderResult(ok=False, error="mermaid-cli (mmdc) is not installed")

    with tempfile.TemporaryDirectory() as tmp:
        in_path = Path(tmp) / "diagram.mmd"
        out_path = Path(tmp) / "diagram.svg"
        in_path.write_text(source, encoding="utf-8")
        try:
            proc = subprocess.run(
                mmdc_command(str(in_path), str(out_path), "transparent"),
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return RenderResult(ok=False, error="Mermaid render timed out")

        if proc.returncode != 0 or not out_path.exists():
            message = (proc.stderr or proc.stdout or "Mermaid render failed").strip()
            return RenderResult(ok=False, error=message)

        return RenderResult(ok=True, svg=out_path.read_text(encoding="utf-8"))


def validate(source: str) -> str | None:
    """Return an error message if the Mermaid source is invalid, else ``None``."""
    result = render(source)
    return None if result.ok else result.error
