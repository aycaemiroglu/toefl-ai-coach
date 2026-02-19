"""
Tests for TOEFL AI Coach backend: word_count, sentence_count, confidence, calibration,
length evaluation, and the unified API response contract.
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

os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from main import (
    FULL_CONFIDENCE_WORDS,
    MIN_WORDS,
    RECOMMENDED_WORDS,
    Subscores,
    _compute_calibration,
    _compute_confidence,
    _compute_length_evaluation,
    app,
    sentence_count,
    word_count,
)


# --- Word count / sentence count ------------------------------------------------
class TestWordCount:
    def test_empty_string(self):
        assert word_count("") == 0

    def test_single_word(self):
        assert word_count("hello") == 1

    def test_multiple_words(self):
        assert word_count("one two three four five") == 5

    def test_leading_trailing_spaces(self):
        assert word_count("  a  b  c  ") == 3

    def test_exactly_min_words(self):
        text = "word " * (MIN_WORDS - 1) + "word"
        assert word_count(text) == MIN_WORDS


class TestSentenceCount:
    def test_empty_string(self):
        assert sentence_count("") == 0

    def test_single_sentence(self):
        assert sentence_count("Hello world.") == 1

    def test_multiple_sentences(self):
        assert sentence_count("First. Second! Third?") == 3

    def test_no_punctuation(self):
        assert sentence_count("no punctuation here") == 1


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
        assert conf.numeric_score_0_100 >= 80
        assert conf.reasons
        assert conf.signals.word_count == 260

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
        assert any("shorter" in r.lower() or "length" in r.lower() for r in conf.reasons)

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
        assert 0 <= conf.numeric_score_0_100 <= 100

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


# --- Calibration -----------------------------------------------------------------
class TestComputeCalibration:
    def test_long_essay_no_penalty(self):
        cal = _compute_calibration(250, 26.0)
        assert cal.length_factor == 1.0
        assert cal.calibrated_score == 26.0

    def test_exactly_recommended_words(self):
        cal = _compute_calibration(RECOMMENDED_WORDS, 24.0)
        assert cal.length_factor == 1.0
        assert cal.calibrated_score == 24.0

    def test_short_essay_penalty(self):
        cal = _compute_calibration(110, 26.0)
        assert cal.length_factor == round(110 / RECOMMENDED_WORDS, 4)
        assert cal.calibrated_score == 13.0

    def test_moderately_short_essay(self):
        cal = _compute_calibration(200, 24.0)
        expected_factor = round(200 / RECOMMENDED_WORDS, 4)
        assert cal.length_factor == expected_factor

    def test_calibrated_score_clamped(self):
        cal = _compute_calibration(50, 30.0)
        assert 0 <= cal.calibrated_score <= 30
        cal2 = _compute_calibration(300, 0.0)
        assert cal2.calibrated_score == 0.0


# --- Length evaluation -----------------------------------------------------------
class TestComputeLengthEvaluation:
    def test_short_tier(self):
        le = _compute_length_evaluation(150)
        assert le.tier == "short"
        assert "calibrated" in le.message.lower()

    def test_recommended_tier(self):
        le = _compute_length_evaluation(220)
        assert le.tier == "recommended"
        assert "full score" in le.message.lower()

    def test_recommended_tier_upper_bound(self):
        le = _compute_length_evaluation(249)
        assert le.tier == "recommended"

    def test_ideal_tier(self):
        le = _compute_length_evaluation(250)
        assert le.tier == "ideal"
        assert "maximum confidence" in le.message.lower()

    def test_ideal_tier_long(self):
        le = _compute_length_evaluation(400)
        assert le.tier == "ideal"


class TestCalibrationConfidenceIntegration:
    def test_calibration_delta_adds_confidence_reason(self):
        subscores = Subscores(
            task_response=4.0,
            coherence_cohesion=4.0,
            lexical_resource=4.0,
            grammar=4.0,
        )
        conf = _compute_confidence(
            word_count=180,
            subscores=subscores,
            final_score=24.0,
            weaknesses=[],
            calibration_delta=4.4,
        )
        assert any("calibration" in r.lower() for r in conf.reasons)

    def test_no_calibration_penalty_when_long_enough(self):
        subscores = Subscores(
            task_response=4.0,
            coherence_cohesion=4.0,
            lexical_resource=4.0,
            grammar=4.0,
        )
        conf = _compute_confidence(
            word_count=250,
            subscores=subscores,
            final_score=24.0,
            weaknesses=[],
            calibration_delta=0.0,
        )
        assert not any("calibration" in r.lower() for r in conf.reasons)


# --- Unified API contract --------------------------------------------------------
MOCK_LLM_PAYLOAD = {
    "subscores": {
        "task_response": 4.0,
        "coherence_cohesion": 4.0,
        "lexical_resource": 4.0,
        "grammar": 4.0,
    },
    "estimated_score": 24.0,
    "strengths": [
        {"label": "Clear thesis", "explanation": "The position is stated clearly.", "evidence": None}
    ],
    "weaknesses": [
        {"label": "Some repetition", "explanation": "Words are repeated.", "evidence": None, "evidence_reason": "Conceptual issue not tied to a single sentence."}
    ],
    "top_fixes": ["Fix A", "Fix B", "Fix C"],
    "rewrite_first_paragraph": "Technology has changed how we live. I believe that...",
}


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

    def test_unified_response_contract_short_essay(self, client):
        essay_120 = " ".join(["word"] * 120)
        with patch("main._call_groq", return_value=json.dumps(MOCK_LLM_PAYLOAD)):
            r = client.post(
                "/api/evaluate",
                json={"prompt": "Do you agree?", "essay": essay_120},
            )
        assert r.status_code == 200
        data = r.json()

        # Top-level keys present
        assert "request_id" in data
        assert "model_name" in data
        assert "timestamps" in data
        assert "text_stats" in data
        assert "rubric" in data
        assert "scoring" in data
        assert "confidence" in data
        assert "length_evaluation" in data
        assert "evidence" in data
        assert "top_fixes" in data

        # Timestamps
        assert "received_at" in data["timestamps"]
        assert "completed_at" in data["timestamps"]

        # Text stats
        assert data["text_stats"]["word_count"] == 120
        assert data["text_stats"]["sentence_count"] >= 1

        # Rubric (new key names)
        rubric = data["rubric"]
        assert rubric["task_response"] == 4.0
        assert rubric["coherence"] == 4.0
        assert rubric["lexical"] == 4.0
        assert rubric["grammar"] == 4.0

        # Scoring
        scoring = data["scoring"]
        assert scoring["raw_score_30"] == 24.0
        assert scoring["length_factor"] < 1.0
        assert scoring["calibrated_score_30"] < 24.0
        assert scoring["calibrated_score_30"] == data["estimated_score"]

        # Confidence (new field name)
        assert data["confidence"]["level"] in ("Low", "Medium", "High")
        assert 0 <= data["confidence"]["numeric_score_0_100"] <= 100

        # Length evaluation
        assert data["length_evaluation"]["tier"] == "short"
        assert "calibrated" in data["length_evaluation"]["message"].lower()

        # Evidence
        assert len(data["evidence"]["strengths"]) >= 1
        assert len(data["evidence"]["weaknesses"]) >= 1
        s0 = data["evidence"]["strengths"][0]
        assert "label" in s0 and "explanation" in s0
        w0 = data["evidence"]["weaknesses"][0]
        assert "label" in w0 and "explanation" in w0

        # Backward-compat aliases
        assert data["word_count"] == 120
        assert "subscores" in data
        assert data["subscores"]["task_response"] == 4.0
        assert data["subscores"]["coherence_cohesion"] == 4.0

    def test_unified_response_long_essay(self, client):
        essay_250 = " ".join(["word"] * 250)
        with patch("main._call_groq", return_value=json.dumps(MOCK_LLM_PAYLOAD)):
            r = client.post(
                "/api/evaluate",
                json={"prompt": "Do you agree?", "essay": essay_250},
            )
        assert r.status_code == 200
        data = r.json()
        assert data["scoring"]["length_factor"] == 1.0
        assert data["scoring"]["raw_score_30"] == data["scoring"]["calibrated_score_30"]
        assert data["length_evaluation"]["tier"] == "ideal"
        assert data["estimated_score"] == 24.0

    def test_prompt_id_passthrough(self, client):
        essay_250 = " ".join(["word"] * 250)
        with patch("main._call_groq", return_value=json.dumps(MOCK_LLM_PAYLOAD)):
            r = client.post(
                "/api/evaluate",
                json={"prompt": "Do you agree?", "essay": essay_250, "prompt_id": "p01"},
            )
        assert r.status_code == 200
        assert r.json()["prompt_id"] == "p01"
