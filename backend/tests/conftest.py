"""
Shared fixtures for the TOEFL evaluator test suite.

All tests mock _call_groq so no real LLM calls are made.
Each fixture essay has a deterministic mock response in fixtures/essays.json.
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

from main import app

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


def _load_essays() -> dict:
    with open(FIXTURES_DIR / "essays.json") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def essays_data():
    return _load_essays()


@pytest.fixture(scope="session")
def prompt_text(essays_data):
    return essays_data["prompt"]


@pytest.fixture(scope="session")
def prompt_id(essays_data):
    return essays_data["prompt_id"]


@pytest.fixture(params=["short", "recommended", "ideal"])
def essay_key(request):
    """Parametrize over all three essay tiers."""
    return request.param


@pytest.fixture
def essay_text(essays_data, essay_key):
    return essays_data["essays"][essay_key]["text"]


@pytest.fixture
def mock_llm_response(essays_data, essay_key):
    return essays_data["mock_llm_responses"][essay_key]


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def evaluate_result(client, prompt_text, prompt_id, essay_text, mock_llm_response):
    """
    POST /api/evaluate with a mocked LLM response.
    Returns (status_code, response_json, essay_text).
    """
    with patch("main._call_groq", return_value=json.dumps(mock_llm_response)):
        r = client.post(
            "/api/evaluate",
            json={"prompt": prompt_text, "essay": essay_text, "prompt_id": prompt_id},
        )
    return r.status_code, r.json(), essay_text
