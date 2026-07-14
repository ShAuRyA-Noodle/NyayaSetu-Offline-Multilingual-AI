"""
Text cleaning for scraped scheme content.

myScheme returns two content shapes:
1. Markdown strings (``*_md`` fields) — with occasional mojibake bullet chars.
2. Slate rich-text trees (lists of nested {type, children, text} nodes) — used
   for application-process steps and eligibility.

Both are converted to clean, human-readable plain text suitable for embedding
and for showing to citizens.
"""

from __future__ import annotations

import re
from typing import Any, List

# Replacement char that shows up where the source had bad-encoded bullets /
# rupee / smart-quotes. We drop it and rely on surrounding punctuation.
_REPLACEMENT = "�"

_MD_LINK = re.compile(r"\[([^\]]+)\]\((?:[^)]+)\)")       # [text](url) -> text
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")            # images -> drop
_HTML_TAG = re.compile(r"<[^>]+>")                        # <br>, etc.
_MULTISPACE = re.compile(r"[ \t]+")
_MULTINEWLINE = re.compile(r"\n{3,}")
_MD_EMPHASIS = re.compile(r"(\*\*|__|\*|_|`)")            # bold/italic/code marks


def clean_markdown(md: str | None) -> str:
    """Strip markdown/HTML to readable plain text; repair mojibake."""
    if not md:
        return ""
    text = md.replace(_REPLACEMENT, " ")
    text = _MD_IMAGE.sub("", text)
    text = _MD_LINK.sub(r"\1", text)
    text = _HTML_TAG.sub("\n", text)
    text = _MD_EMPHASIS.sub("", text)
    # Normalize markdown list markers to a consistent bullet.
    lines: List[str] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)          # headings
        line = re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "• ", line)  # list -> bullet
        lines.append(line)
    text = "\n".join(lines)
    text = _MULTISPACE.sub(" ", text)
    text = _MULTINEWLINE.sub("\n\n", text)
    return text.strip()


def slate_to_text(nodes: Any) -> str:
    """
    Flatten a Slate rich-text tree (or list of trees) into plain text.

    Preserves paragraph/step boundaries as newlines and list items as bullets.
    """
    if nodes is None:
        return ""
    if isinstance(nodes, str):
        return nodes
    out: List[str] = []

    def walk(node: Any, in_list_item: bool = False) -> None:
        if isinstance(node, list):
            for n in node:
                walk(n, in_list_item)
            return
        if not isinstance(node, dict):
            if node:
                out.append(str(node))
            return
        ntype = node.get("type", "")
        # Leaf text node.
        if "text" in node and "children" not in node:
            txt = node.get("text", "")
            if txt:
                out.append(txt)
            return
        is_item = ntype == "list_item"
        is_block = ntype in (
            "paragraph",
            "block_quote",
            "align_justify",
            "heading_one",
            "heading_two",
            "heading_three",
        )
        if is_item:
            out.append("\n• ")
        elif is_block:
            out.append("\n")
        walk(node.get("children", []), in_list_item or is_item)

    walk(nodes)
    text = "".join(out)
    text = _MULTISPACE.sub(" ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = _MULTINEWLINE.sub("\n\n", text)
    return text.strip()


def truncate(text: str, max_chars: int = 8000) -> str:
    """Cap a field's length (defensive — some descriptions are very long)."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    # Avoid cutting mid-word.
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip() + " …"
