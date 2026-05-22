"""Parse and emit reusable-block Markdown files (YAML frontmatter + body)."""
from __future__ import annotations

import yaml


def parse_block_file(text: str) -> tuple[dict, str]:
    """Split a ``--- frontmatter --- body`` file into (metadata, body markdown).

    Files without frontmatter yield an empty metadata dict and the whole text
    as the body.
    """
    stripped = text.lstrip()
    if not stripped.startswith("---"):
        return {}, text.strip()
    rest = stripped[3:]
    end = rest.find("\n---")
    if end == -1:
        return {}, text.strip()
    front = rest[:end]
    body = rest[end + 4 :]
    meta = yaml.safe_load(front) or {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, body.strip()


def render_block_file(meta: dict, body: str) -> str:
    """Inverse of :func:`parse_block_file` — emit frontmatter + body."""
    front = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{front}\n---\n\n{body.strip()}\n"
