"""
Harness JSONL output validation tests.

Guarantees:
- Every line in results.jsonl parses as valid JSON
- No banned alias keys appear in any result record (deep scan)
- All required canonical fields are present in each successful record
- _meta field is present with source_file
- overall_score == scoring.final in every record
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

_backend = Path(__file__).resolve().parent.parent
_project_root = _backend.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from eval_harness.runner import evaluate_batch

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BANNED_ALIASES = frozenset({
    "estimated_score",
    "subscores",
    "coherence_cohesion",
    "lexical_resource",
})

ALLOWED_NESTED = frozenset({
    "text_stats.word_count",
    "confidence.signals.word_count",
    "timestamps.latency_ms",
})

CANONICAL_TOP_KEYS = {
    "request_id", "model_name", "overall_score",
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
        {"label": "Clear thesis", "explanation": "Well stated.", "evidence": None}
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

TINY_ESSAYS = [
    {
        "essay": " ".join(["word"] * 150),
        "prompt": "Do you agree?",
        "prompt_id": "test_short",
        "level": "short",
        "source_file": "essay_short.txt",
    },
    {
        "essay": " ".join(["word"] * 250),
        "prompt": "Do you agree?",
        "prompt_id": "test_ideal",
        "level": "ideal",
        "source_file": "essay_ideal.txt",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deep_scan(obj, banned, path=""):
    """Recursively collect paths where a banned key name appears."""
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def jsonl_lines(tmp_path_factory):
    """Run evaluate_batch once with mocked LLM; return list of raw line strings."""
    tmpdir = tmp_path_factory.mktemp("harness")
    out = tmpdir / "results.jsonl"
    with patch("main._call_groq", return_value=MOCK_LLM):
        evaluate_batch(TINY_ESSAYS, out)
    return out.read_text().strip().splitlines()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestJSONLFormat:
    """Basic JSONL structural guarantees."""

    def test_correct_line_count(self, jsonl_lines):
        assert len(jsonl_lines) == len(TINY_ESSAYS)

    def test_every_line_is_valid_json(self, jsonl_lines):
        for i, line in enumerate(jsonl_lines):
            try:
                json.loads(line)
            except json.JSONDecodeError:
                pytest.fail(f"Line {i} is not valid JSON: {line[:120]}")


class TestJSONLCanonicalSchema:
    """Each record must follow the canonical schema with no aliases."""

    def test_canonical_keys_present(self, jsonl_lines):
        for i, line in enumerate(jsonl_lines):
            record = json.loads(line)
            if "_error" in record:
                continue
            missing = CANONICAL_TOP_KEYS - set(record.keys())
            assert not missing, f"Line {i}: missing canonical keys {missing}"

    def test_no_alias_keys_deep(self, jsonl_lines):
        for i, line in enumerate(jsonl_lines):
            record = json.loads(line)
            if "_error" in record:
                continue
            found = _deep_scan(record, BANNED_ALIASES)
            leaked = [p for p in found if p not in ALLOWED_NESTED]
            assert not leaked, f"Line {i}: banned alias keys found: {leaked}"

    def test_no_root_alias_keys(self, jsonl_lines):
        root_banned = BANNED_ALIASES | {"word_count", "latency_ms"}
        for i, line in enumerate(jsonl_lines):
            record = json.loads(line)
            if "_error" in record:
                continue
            found = root_banned & set(record.keys())
            assert not found, f"Line {i}: root-level aliases: {found}"

    def test_overall_score_equals_final(self, jsonl_lines):
        for i, line in enumerate(jsonl_lines):
            record = json.loads(line)
            if "_error" in record:
                continue
            assert record["overall_score"] == record["scoring"]["final"], (
                f"Line {i}: overall_score ({record['overall_score']}) "
                f"!= scoring.final ({record['scoring']['final']})"
            )

    def test_meta_present(self, jsonl_lines):
        for i, line in enumerate(jsonl_lines):
            record = json.loads(line)
            assert "_meta" in record, f"Line {i}: missing _meta"
            assert "source_file" in record["_meta"], f"Line {i}: missing _meta.source_file"

    def test_source_files_match_input(self, jsonl_lines):
        expected_files = {e["source_file"] for e in TINY_ESSAYS}
        actual_files = {json.loads(line)["_meta"]["source_file"] for line in jsonl_lines}
        assert actual_files == expected_files
