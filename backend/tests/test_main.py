"""
Tests for TOEFL AI Coach backend: word_count, confidence computation, and API.
Run from repo root: pytest backend/tests/ -v
Or from backend: pytest tests/ -v
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Allow importing main without real API key (evaluate calls are mocked where needed)
os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

# Ensure backend is on path when running from repo root
_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from main import (
    MIN_WORDS,
    Subscores,
    _compute_confidence,
    app,
    word_count,
)


# --- Word count -----------------------------------------------------------------
class TestWordCount:
    def test_empty_string(self):
        assert word_count("") == 0

    def test_single_word(self):
        assert word_count("hello") == 1

    def test_multiple_words(self):
        assert word_count("one two three four five") == 5

    def test_leading_trailing_spaces(self):
        # split() collapses multiple spaces; we count tokens
        assert word_count("  a  b  c  ") == 3

    def test_exactly_min_words(self):
        text = "word " * (MIN_WORDS - 1) + "word"
        assert word_count(text) == MIN_WORDS


# --- Confidence computation -----------------------------------------------------
class TestComputeConfidence:
    def test_long_essay_balanced_subscores_high_confidence(self):
        subscores = Subscores(
            task_response=4.0,
            coherence_cohesion=4.0,
            lexical_resource=4.0,
            grammar=4.0,
        )
        conf = _compute_confidence(
            word_count=260,
            subscores=subscores,
            final_score=24.0,
            weaknesses=[],
        )
        assert conf.level == "High"
        assert conf.numeric_score >= 80
        assert conf.reasons
        assert conf.signals.word_count == 260
        assert conf.signals.subscore_variance == 0.0

    def test_short_essay_penalty(self):
        subscores = Subscores(
            task_response=4.0,
            coherence_cohesion=4.0,
            lexical_resource=4.0,
            grammar=4.0,
        )
        conf = _compute_confidence(
            word_count=170,
            subscores=subscores,
            final_score=22.0,
            weaknesses=[],
        )
        # Below 180: -35; should have "shorter than recommended" reason
        assert any("shorter" in r.lower() or "length" in r.lower() for r in conf.reasons)
        assert conf.signals.word_count == 170

    def test_subscore_variance_penalty(self):
        subscores = Subscores(
            task_response=2.0,
            coherence_cohesion=4.0,
            lexical_resource=4.0,
            grammar=5.0,
        )
        conf = _compute_confidence(
            word_count=250,
            subscores=subscores,
            final_score=20.0,
            weaknesses=[],
        )
        assert conf.signals.subscore_variance == 3.0
        assert any("variance" in r.lower() or "vary" in r.lower() for r in conf.reasons)

    def test_high_score_short_essay_penalty(self):
        subscores = Subscores(
            task_response=5.0,
            coherence_cohesion=5.0,
            lexical_resource=5.0,
            grammar=5.0,
        )
        conf = _compute_confidence(
            word_count=200,
            subscores=subscores,
            final_score=26.0,
            weaknesses=[],
        )
        # word_count < 220 and final_score >= 25 -> extra penalty
        assert any("short" in r.lower() or "generosity" in r.lower() for r in conf.reasons)

    def test_confidence_score_clamped_0_100(self):
        subscores = Subscores(
            task_response=1.0,
            coherence_cohesion=1.0,
            lexical_resource=1.0,
            grammar=1.0,
        )
        conf = _compute_confidence(
            word_count=100,
            subscores=subscores,
            final_score=28.0,
            weaknesses=[{"label": "x"}, {"label": "y"}, {"label": "counterargument"}],
        )
        assert 0 <= conf.numeric_score <= 100

    def test_counterargument_weakness_signal(self):
        conf = _compute_confidence(
            word_count=250,
            subscores=Subscores(
                task_response=4.5,
                coherence_cohesion=4.0,
                lexical_resource=4.0,
                grammar=4.0,
            ),
            final_score=24.0,
            weaknesses=[{"label": "Missing counter-argument"}],
        )
        assert conf.signals.has_counterargument_weakness is True


# --- API -------------------------------------------------------------------------
class TestEvaluateEndpoint:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_evaluate_rejects_essay_below_min_words(self, client):
        short_essay = "one two three"
        r = client.post(
            "/api/evaluate",
            json={"prompt": "Do you agree?", "essay": short_essay},
        )
        assert r.status_code == 422
        assert "120" in r.json()["detail"]
        assert "at least" in r.json()["detail"].lower()

    def test_evaluate_accepts_essay_at_min_words_with_mock(self, client):
        payload = {
            "subscores": {
                "task_response": 4.0,
                "coherence_cohesion": 4.0,
                "lexical_resource": 4.0,
                "grammar": 4.0,
            },
            "estimated_score": 24.0,
            "strengths": ["Clear thesis", "Good examples"],
            "weaknesses": ["Some repetition"],
            "top_fixes": ["Fix A", "Fix B", "Fix C"],
            "rewrite_first_paragraph": "Technology has changed how we live. I believe that...",
        }
        essay_120 = " ".join(["word"] * 120)
        with patch("main._call_groq", return_value=json.dumps(payload)):
            r = client.post(
                "/api/evaluate",
                json={"prompt": "Do you agree?", "essay": essay_120},
            )
        assert r.status_code == 200
        data = r.json()
        assert data["word_count"] == 120
        assert data["estimated_score"] == 24.0
        assert "confidence" in data
        assert data["confidence"]["level"] in ("Low", "Medium", "High")
        assert 0 <= data["confidence"]["numeric_score"] <= 100
        assert "reasons" in data["confidence"]
        assert "signals" in data["confidence"]
