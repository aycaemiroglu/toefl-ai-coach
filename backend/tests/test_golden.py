"""
Golden / snapshot tests for the stable JSON contract.

Protects against:
- Accidental changes to response shape (added/removed/renamed keys)
- Unintended changes to deterministic scoring/calibration/confidence values

Dynamic fields (request_id, timestamps, latency_ms) are stripped before comparison.
To regenerate golden files after an intentional contract change:
    python -m tests.update_golden
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from main import app

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"

DYNAMIC_KEYS = {"request_id", "timestamps", "latency_ms"}


def _strip_dynamic(data: dict) -> dict:
    """Remove fields that change between runs."""
    return {k: v for k, v in data.items() if k not in DYNAMIC_KEYS}


def _load_essays() -> dict:
    with open(FIXTURES_DIR / "essays.json") as f:
        return json.load(f)


def _get_response(key: str) -> dict:
    essays = _load_essays()
    client = TestClient(app)
    mock_resp = essays["mock_llm_responses"][key]
    with patch("main._call_groq", return_value=json.dumps(mock_resp)):
        r = client.post(
            "/api/evaluate",
            json={
                "prompt": essays["prompt"],
                "essay": essays["essays"][key]["text"],
                "prompt_id": essays["prompt_id"],
            },
        )
    assert r.status_code == 200
    return r.json()


@pytest.mark.parametrize("essay_key", ["short", "recommended", "ideal"])
class TestGoldenSnapshot:
    def test_response_matches_golden(self, essay_key):
        golden_path = GOLDEN_DIR / f"{essay_key}.json"
        if not golden_path.exists():
            pytest.skip(
                f"Golden file {golden_path.name} not found. "
                f"Run: python -m tests.update_golden"
            )

        with open(golden_path) as f:
            expected = json.load(f)

        actual = _strip_dynamic(_get_response(essay_key))

        assert actual == expected, (
            f"Golden mismatch for {essay_key}. "
            f"If this is intentional, run: python -m tests.update_golden"
        )
