"""
Normalizer — maps a raw myScheme detail tree into the RAG-ready scheme shape.

Output matches the `schemes` table used by the chunker/RAG engine:
    scheme_name, department, eligibility, benefits, process
plus rich metadata for `schemes_metadata` (category, tags, level, state,
target audience, slug, source URLs).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .text_clean import clean_markdown, slate_to_text, truncate


@dataclass
class NormalizedScheme:
    """A single cleaned, RAG-ready government scheme."""

    slug: str
    scheme_name: str
    department: str
    eligibility: str
    benefits: str
    process: str
    # Metadata (→ schemes_metadata)
    category: str = ""
    sub_category: str = ""
    level: str = ""             # 'central' | 'state'
    state: str = ""
    target_audience: str = ""
    brief_description: str = ""
    tags: List[str] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)
    source: str = "myscheme.gov.in"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def has_content(self) -> bool:
        """True if the scheme has at least one non-empty RAG section."""
        return bool(self.eligibility or self.benefits or self.process)


def _label(obj: Any) -> str:
    """Extract a human label from myScheme's {value,label} or list thereof."""
    if isinstance(obj, dict):
        return str(obj.get("label") or obj.get("value") or "").strip()
    if isinstance(obj, list) and obj:
        return ", ".join(_label(o) for o in obj if _label(o))
    if isinstance(obj, str):
        return obj.strip()
    return ""


def _value(obj: Any) -> str:
    """Extract the canonical machine value (not the display label)."""
    if isinstance(obj, dict):
        return str(obj.get("value") or "").strip().lower()
    if isinstance(obj, str):
        return obj.strip().lower()
    return ""


def _department(basic: Dict[str, Any]) -> str:
    """Prefer nodal ministry; fall back to nodal department; then agency."""
    for key in ("nodalMinistryName", "nodalDepartmentName", "implementingAgency"):
        lbl = _label(basic.get(key))
        if lbl:
            return lbl
    return "Government of India"


def _application_process(app_proc: Any) -> str:
    """Flatten the applicationProcess list (per-mode Slate trees)."""
    if not isinstance(app_proc, list):
        return slate_to_text(app_proc)
    parts: List[str] = []
    for block in app_proc:
        if not isinstance(block, dict):
            continue
        mode = str(block.get("mode", "")).strip()
        body = slate_to_text(block.get("process", []))
        if body:
            parts.append(f"[{mode}]\n{body}" if mode else body)
    return "\n\n".join(parts).strip()


def normalize_scheme(detail: Dict[str, Any]) -> Optional[NormalizedScheme]:
    """
    Convert a raw detail tree (from ``MySchemeClient.get_scheme_detail``) into a
    ``NormalizedScheme``. Returns None if the record has no usable name.
    """
    basic = detail.get("basicDetails") or {}
    content = detail.get("schemeContent") or {}
    elig = detail.get("eligibilityCriteria") or {}
    slug = detail.get("_slug") or basic.get("slug") or ""

    name = (basic.get("schemeName") or "").strip()
    if not name:
        return None

    # Eligibility: prefer cleaned markdown, fall back to slate nodes.
    eligibility = clean_markdown(elig.get("eligibilityDescription_md"))
    if not eligibility:
        eligibility = slate_to_text(elig.get("eligibilityDescription"))

    # Benefits: dedicated benefits_md, fall back to the detailed description.
    benefits = clean_markdown(content.get("benefits_md"))
    if not benefits:
        benefits = clean_markdown(content.get("detailedDescription_md"))

    process = _application_process(detail.get("applicationProcess"))

    references = content.get("references") or []
    source_urls = [
        r.get("url", "").strip()
        for r in references
        if isinstance(r, dict) and r.get("url")
    ]

    return NormalizedScheme(
        slug=slug,
        scheme_name=truncate(name, 400),
        department=truncate(_department(basic), 300),
        eligibility=truncate(eligibility),
        benefits=truncate(benefits),
        process=truncate(process),
        category=_label(basic.get("schemeCategory")),
        sub_category=_label(basic.get("schemeSubCategory")),
        level=_value(basic.get("level")) or "",
        state=_label(basic.get("state")),
        target_audience=_label(basic.get("targetBeneficiaries"))
        or _label(basic.get("schemeFor")),
        brief_description=clean_markdown(content.get("briefDescription"))[:1000],
        tags=[t for t in (basic.get("tags") or []) if isinstance(t, str)][:25],
        source_urls=source_urls[:10],
    )
