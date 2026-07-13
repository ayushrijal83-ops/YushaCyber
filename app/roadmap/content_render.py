"""Lesson content rendering.

Loads a lesson's markdown from disk (referenced by ``lesson.content_path``)
and converts it to sanitised HTML. Content lives under a single content
root so a stored path can never escape it (no directory traversal), and
the converted HTML is bleach-sanitised to a safe tag/attribute allowlist
before it reaches the template.

If the file is missing, ``render_lesson_content`` returns None so the
view can show a friendly "coming soon" message instead of crashing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import bleach
import markdown
from flask import current_app

# Markdown files live under <project>/app/content/<content_path>.
# The seed stores paths like "roadmap/beginner/<module>/<lesson>.md".
CONTENT_ROOT_NAME = "content"

# Tags/attributes permitted in rendered lesson HTML.
_ALLOWED_TAGS = [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr",
    "strong", "em", "del", "sub", "sup",
    "ul", "ol", "li",
    "blockquote",
    "a", "img",
    "code", "pre",
    "table", "thead", "tbody", "tr", "th", "td",
    "span", "div",
]
_ALLOWED_ATTRS = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title"],
    "code": ["class"],       # language hint from fenced blocks
    "span": ["class"],
    "th": ["align"],
    "td": ["align"],
}


def _content_root() -> Path:
    """Absolute path to the lesson content directory (app/content)."""
    return Path(current_app.root_path) / CONTENT_ROOT_NAME


def _resolve_safe(content_path: str) -> Optional[Path]:
    """Resolve content_path under the content root, or None if it escapes.

    Guards against directory traversal: the resolved path must stay
    inside the content root.
    """
    if not content_path:
        return None
    root = _content_root().resolve()
    candidate = (root / content_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None  # attempted to escape the content root
    return candidate


def render_lesson_content(content_path: Optional[str]) -> Optional[str]:
    """Return sanitised HTML for a lesson, or None if the file is absent."""
    path = _resolve_safe(content_path or "")
    if path is None or not path.is_file():
        return None

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None

    html = markdown.markdown(
        raw,
        extensions=["fenced_code", "tables", "sane_lists"],
        output_format="html5",
    )
    return bleach.clean(html, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS)
