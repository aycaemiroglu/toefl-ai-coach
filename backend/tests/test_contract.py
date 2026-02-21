"""
Contract / schema tests for the canonical API response.

Protects against:
- Missing required top-level keys
- Pydantic model validation failures (field types, ranges)
- Alias fields leaking back into the response
"""
import sys
from pathlib import Path

from pydantic import TypeAdapter

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from main import EvaluateResponse

BANNED_ALIAS_KEYS = {"estimated_score", "subscores", "coherence_cohesion", "lexical_resource", "word_count", "latency_ms"}


def _deep_find_keys(obj, banned: set[str], path: str = "") -> list[str]:
    """Recursively scan a dict/list for banned key names."""
    found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{path}.{k}" if path else k
            if k in banned:
                found.append(full)
            found.extend(_deep_find_keys(v, banned, full))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found.extend(_deep_find_keys(item, banned, f"{path}[{i}]"))
    return found


class TestResponseContract:
    """Every fixture essay must produce a valid, complete response."""

    def test_status_200(self, evaluate_result):
        status, _, _ = evaluate_result
        assert status == 200

    def test_pydantic_validation(self, evaluate_result):
        """Response must parse cleanly through the Pydantic model."""
        _, data, _ = evaluate_result
        adapter = TypeAdapter(EvaluateResponse)
        obj = adapter.validate_python(data)
        assert obj.request_id

    def test_required_top_level_keys(self, evaluate_result):
        _, data, _ = evaluate_result
        required = {
            "request_id", "model_name", "overall_score", "timestamps",
            "text_stats", "rubric", "scoring", "confidence", "length",
            "evidence", "top_fixes", "rewrite_first_paragraph",
        }
        missing = required - set(data.keys())
        assert not missing, f"Missing keys: {missing}"

    def test_timestamps_present(self, evaluate_result):
        _, data, _ = evaluate_result
        ts = data["timestamps"]
        assert "received_at" in ts and ts["received_at"]
        assert "completed_at" in ts and ts["completed_at"]
        assert ts["latency_ms"] >= 0

    def test_text_stats_positive(self, evaluate_result):
        _, data, _ = evaluate_result
        assert data["text_stats"]["word_count"] > 0
        assert data["text_stats"]["sentence_count"] > 0

    def test_rubric_ranges(self, evaluate_result):
        _, data, _ = evaluate_result
        for key in ("task_response", "coherence", "lexical", "grammar"):
            val = data["rubric"][key]
            assert 0 <= val <= 5, f"rubric.{key}={val} out of [0,5]"

    def test_scoring_ranges(self, evaluate_result):
        _, data, _ = evaluate_result
        s = data["scoring"]
        assert 0 <= s["raw"] <= 30
        assert 0 <= s["length_penalty"] <= 1
        assert 0 <= s["final"] <= 30

    def test_overall_score_equals_final(self, evaluate_result):
        _, data, _ = evaluate_result
        assert data["overall_score"] == data["scoring"]["final"]

    def test_confidence_ranges(self, evaluate_result):
        _, data, _ = evaluate_result
        c = data["confidence"]
        assert c["level"] in ("Low", "Medium", "High")
        assert 0 <= c["score"] <= 100
        assert isinstance(c["reasons"], list) and len(c["reasons"]) >= 1

    def test_length_valid_tier(self, evaluate_result):
        _, data, _ = evaluate_result
        assert data["length"]["tier"] in ("short", "recommended", "ideal")
        assert data["length"]["message"]

    def test_evidence_structure(self, evaluate_result):
        _, data, _ = evaluate_result
        ev = data["evidence"]
        assert isinstance(ev["strengths"], list)
        assert isinstance(ev["weaknesses"], list)
        for s in ev["strengths"]:
            assert "label" in s and "explanation" in s
        for w in ev["weaknesses"]:
            assert "label" in w and "explanation" in w

    def test_top_fixes_exactly_three(self, evaluate_result):
        _, data, _ = evaluate_result
        assert len(data["top_fixes"]) == 3
        assert all(isinstance(f, str) and f for f in data["top_fixes"])

    def test_prompt_id_passthrough(self, evaluate_result):
        _, data, _ = evaluate_result
        assert data["prompt_id"] == "tech_easier_v1"

    def test_no_alias_keys_at_root(self, evaluate_result):
        """Alias fields must NOT appear at the top level."""
        _, data, _ = evaluate_result
        for banned in BANNED_ALIAS_KEYS:
            assert banned not in data, f"Alias '{banned}' found at root level"

    def test_no_alias_keys_anywhere_deep(self, evaluate_result):
        """Deep scan: no banned alias key name anywhere in the response tree."""
        _, data, _ = evaluate_result
        found = _deep_find_keys(data, BANNED_ALIAS_KEYS)
        # word_count is a legitimate nested field, latency_ms moved into timestamps
        allowed_paths = {
            "text_stats.word_count",
            "confidence.signals.word_count",
            "timestamps.latency_ms",
        }
        leaked = [f for f in found if f not in allowed_paths]
        assert not leaked, f"Alias keys found in response: {leaked}"
