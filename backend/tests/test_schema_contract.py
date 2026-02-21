"""
Canonical schema contract tests.

Guarantees:
- All required canonical fields exist at correct nesting levels
- No banned alias keys appear anywhere in the JSON response (deep recursive scan)
- overall_score always equals scoring.final
- scoring.length_penalty matches min(1, word_count / 220) within ±0.0001
- All numeric fields fall within documented ranges:
    rubric fields: [0, 5]
    scoring.raw, scoring.final, overall_score: [0, 30]
    scoring.length_penalty: [0, 1]
    confidence.score: [0, 100]
    confidence.level ∈ {Low, Medium, High}
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from main import RECOMMENDED_WORDS, app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BANNED_ALIASES = frozenset({
    "estimated_score",
    "subscores",
    "coherence_cohesion",
    "lexical_resource",
})

ROOT_BANNED = BANNED_ALIASES | frozenset({"word_count", "latency_ms"})

ALLOWED_NESTED = frozenset({
    "text_stats.word_count",
    "confidence.signals.word_count",
    "timestamps.latency_ms",
})

CANONICAL_TOP_KEYS = {
    "request_id", "prompt_id", "model_name", "overall_score",
    "timestamps", "text_stats", "rubric", "scoring",
    "confidence", "length", "evidence",
    "top_fixes", "rewrite_first_paragraph",
}

MOCK_LLM = json.dumps({
    "estimated_score": 24.0,
    "subscores": {
        "task_response": 4.0, "coherence_cohesion": 4.0,
        "lexical_resource": 4.0, "grammar": 4.0,
    },
    "strengths": [
        {"label": "Clear thesis", "explanation": "Position stated.", "evidence": None}
    ],
    "weaknesses": [
        {
            "label": "Needs depth", "explanation": "Underdeveloped.",
            "evidence": None,
            "evidence_reason": "Conceptual issue not tied to a single sentence.",
        }
    ],
    "top_fixes": ["Develop ideas", "Vary vocabulary", "Add transitions"],
    "rewrite_first_paragraph": "Rewritten paragraph.",
})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deep_scan(obj, banned, path=""):
    """Recursively collect full paths where a banned key name appears."""
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{path}.{k}" if path else k
            if k in banned:
                found.append(full)
            found.extend(_deep_scan(v, banned, full))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found.extend(_deep_scan(item, banned, f"{path}[{i}]"))
    return found


def _call_api(client, wc):
    essay = " ".join(["word"] * wc)
    with patch("main._call_groq", return_value=MOCK_LLM):
        r = client.post(
            "/api/evaluate",
            json={"prompt": "Do you agree?", "essay": essay},
        )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    return r.json()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)


@pytest.fixture(params=[130, 180, 220, 260], ids=["130w", "180w", "220w", "260w"])
def response(api_client, request):
    return _call_api(api_client, request.param)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCanonicalFieldsPresent:
    """Required canonical fields must exist at the correct nesting level."""

    def test_top_level_keys(self, response):
        missing = CANONICAL_TOP_KEYS - set(response.keys())
        assert not missing, f"Missing top-level keys: {missing}"

    def test_rubric_subkeys(self, response):
        for k in ("task_response", "coherence", "lexical", "grammar"):
            assert k in response["rubric"], f"Missing rubric.{k}"

    def test_scoring_subkeys(self, response):
        for k in ("raw", "length_penalty", "final"):
            assert k in response["scoring"], f"Missing scoring.{k}"

    def test_confidence_subkeys(self, response):
        for k in ("level", "score", "reasons", "signals"):
            assert k in response["confidence"], f"Missing confidence.{k}"

    def test_timestamps_subkeys(self, response):
        for k in ("received_at", "completed_at", "latency_ms"):
            assert k in response["timestamps"], f"Missing timestamps.{k}"

    def test_text_stats_subkeys(self, response):
        for k in ("word_count", "sentence_count"):
            assert k in response["text_stats"], f"Missing text_stats.{k}"

    def test_evidence_subkeys(self, response):
        assert "strengths" in response["evidence"]
        assert "weaknesses" in response["evidence"]

    def test_top_fixes_exactly_three(self, response):
        assert len(response["top_fixes"]) == 3


class TestNoAliasKeys:
    """Banned alias keys must not appear anywhere in the response."""

    def test_no_aliases_at_root(self, response):
        found = ROOT_BANNED & set(response.keys())
        assert not found, f"Alias keys at root level: {found}"

    def test_no_aliases_deep_scan(self, response):
        found = _deep_scan(response, BANNED_ALIASES)
        leaked = [p for p in found if p not in ALLOWED_NESTED]
        assert not leaked, f"Alias keys in response tree: {leaked}"


class TestScoreRelationships:
    """Invariant relationships between scoring fields."""

    def test_overall_score_equals_scoring_final(self, response):
        assert response["overall_score"] == response["scoring"]["final"]

    def test_length_penalty_matches_formula(self, response):
        wc = response["text_stats"]["word_count"]
        expected = round(min(1.0, wc / RECOMMENDED_WORDS), 4)
        actual = response["scoring"]["length_penalty"]
        assert abs(actual - expected) < 0.0001, (
            f"length_penalty={actual}, expected={expected} (wc={wc})"
        )

    def test_final_le_raw(self, response):
        assert response["scoring"]["final"] <= response["scoring"]["raw"]


class TestNumericRanges:
    """All numeric values must be within documented bounds."""

    def test_rubric_in_0_5(self, response):
        for k in ("task_response", "coherence", "lexical", "grammar"):
            v = response["rubric"][k]
            assert 0 <= v <= 5, f"rubric.{k}={v} out of [0,5]"

    def test_raw_in_0_30(self, response):
        assert 0 <= response["scoring"]["raw"] <= 30

    def test_final_in_0_30(self, response):
        assert 0 <= response["scoring"]["final"] <= 30

    def test_overall_in_0_30(self, response):
        assert 0 <= response["overall_score"] <= 30

    def test_length_penalty_in_0_1(self, response):
        assert 0 <= response["scoring"]["length_penalty"] <= 1

    def test_confidence_score_in_0_100(self, response):
        assert 0 <= response["confidence"]["score"] <= 100

    def test_confidence_level_valid(self, response):
        assert response["confidence"]["level"] in ("Low", "Medium", "High")

    def test_latency_non_negative(self, response):
        assert response["timestamps"]["latency_ms"] >= 0
