"""
Contract / schema tests for the unified API response.

Protects against:
- Missing required top-level keys
- Pydantic model validation failures (field types, ranges)
- Broken backward-compat aliases
"""
import sys
from pathlib import Path

from pydantic import TypeAdapter

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from main import EvaluateResponse


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
            "request_id", "model_name", "timestamps", "text_stats",
            "rubric", "scoring", "confidence", "length_evaluation",
            "evidence", "top_fixes", "rewrite_first_paragraph",
        }
        missing = required - set(data.keys())
        assert not missing, f"Missing keys: {missing}"

    def test_timestamps_present(self, evaluate_result):
        _, data, _ = evaluate_result
        ts = data["timestamps"]
        assert "received_at" in ts and ts["received_at"]
        assert "completed_at" in ts and ts["completed_at"]

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
        assert 0 <= s["raw_score_30"] <= 30
        assert 0 <= s["length_factor"] <= 1
        assert 0 <= s["calibrated_score_30"] <= 30

    def test_confidence_ranges(self, evaluate_result):
        _, data, _ = evaluate_result
        c = data["confidence"]
        assert c["level"] in ("Low", "Medium", "High")
        assert 0 <= c["numeric_score_0_100"] <= 100
        assert isinstance(c["reasons"], list) and len(c["reasons"]) >= 1

    def test_length_evaluation_valid_tier(self, evaluate_result):
        _, data, _ = evaluate_result
        assert data["length_evaluation"]["tier"] in ("short", "recommended", "ideal")
        assert data["length_evaluation"]["message"]

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

    def test_backward_compat_aliases(self, evaluate_result):
        """Frontend may still depend on these legacy fields."""
        _, data, _ = evaluate_result
        assert "estimated_score" in data
        assert "subscores" in data
        assert "word_count" in data
        assert "latency_ms" in data
        sub = data["subscores"]
        assert all(k in sub for k in ("task_response", "coherence_cohesion", "lexical_resource", "grammar"))

    def test_estimated_score_equals_calibrated(self, evaluate_result):
        """The backward-compat estimated_score must equal scoring.calibrated_score_30."""
        _, data, _ = evaluate_result
        assert data["estimated_score"] == data["scoring"]["calibrated_score_30"]

    def test_prompt_id_passthrough(self, evaluate_result):
        _, data, _ = evaluate_result
        assert data["prompt_id"] == "tech_easier_v1"
