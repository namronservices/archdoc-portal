"""Small shared helpers."""
from __future__ import annotations

import re


def slugify(value: str) -> str:
    """Convert a display name into a URL/path-safe slug."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "item"
