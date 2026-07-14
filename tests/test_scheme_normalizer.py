"""
Tests for the myScheme data pipeline normalizer + text cleaning.

Uses a REAL captured scheme detail (tests/fixtures/myscheme_sample.json) so the
test is deterministic and offline, but exercises genuine portal data — not
synthetic fixtures.
"""

import json
from pathlib import Path

import pytest

from src.data_pipeline.normalizer import normalize_scheme
from src.data_pipeline.text_clean import clean_markdown, slate_to_text

FIXTURE = Path(__file__).parent / "fixtures" / "myscheme_sample.json"


@pytest.fixture
def detail():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_normalize_produces_rag_fields(detail):
    ns = normalize_scheme(detail)
    assert ns is not None
    assert ns.scheme_name  # non-empty name
    assert ns.slug == "namo-shetkari-mahasanman-nidhi-yojana"
    # A real scheme must yield at least one populated RAG section.
    assert ns.has_content()
    assert ns.eligibility or ns.benefits or ns.process


def test_department_resolved(detail):
    ns = normalize_scheme(detail)
    # Department comes from nodal ministry/department — never the empty string.
    assert ns.department
    assert ns.department != "Government of India" or "Agriculture" in ns.department


def test_metadata_extracted(detail):
    ns = normalize_scheme(detail)
    assert ns.category  # schemeCategory label present
    assert isinstance(ns.tags, list)
    assert ns.level in ("central", "state", "")


def test_no_mojibake_replacement_char(detail):
    ns = normalize_scheme(detail)
    for field in (ns.eligibility, ns.benefits, ns.process):
        assert "�" not in field  # the � replacement char is scrubbed


def test_missing_name_returns_none():
    assert normalize_scheme({"basicDetails": {}, "schemeContent": {}}) is None


# ---- text_clean unit tests -------------------------------------------------


def test_clean_markdown_strips_syntax():
    md = "## Heading\n\n- **Bold** item with [link](http://x.com)\n1. second"
    out = clean_markdown(md)
    assert "**" not in out and "##" not in out
    assert "link" in out and "http://x.com" not in out
    assert "• Bold item" in out
    assert "• second" in out


def test_clean_markdown_repairs_mojibake():
    assert "�" not in clean_markdown("�\tRs. 6000 will be transferred")


def test_slate_to_text_flattens_tree():
    tree = [
        {"type": "paragraph", "children": [
            {"text": "Step 1:", "bold": True},
            {"text": " Visit the portal "},
            {"type": "link", "link": "http://p", "children": [{"text": "here"}]},
        ]},
        {"type": "ol_list", "children": [
            {"type": "list_item", "children": [{"text": "First"}]},
            {"type": "list_item", "children": [{"text": "Second"}]},
        ]},
    ]
    out = slate_to_text(tree)
    assert "Step 1:" in out and "Visit the portal" in out and "here" in out
    assert "• First" in out and "• Second" in out


def test_slate_handles_empty():
    assert slate_to_text(None) == ""
    assert slate_to_text([]) == ""
