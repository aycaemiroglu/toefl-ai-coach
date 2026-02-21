"""
Calibration regression tests with 3 fixed essays and deterministic mock responses.

Guarantees:
- ~150-word essay: length_penalty < 1, final score < raw score
- ~190-word essay: length_penalty < 1, final score < raw score
- ~240-word essay: length_penalty == 1.0, final score == raw score
- Exact calibration values match: final = round(raw × min(1, wc/220), 1)
- Pure-function calibration matches end-to-end API calibration
- RECOMMENDED_WORDS constant is 220 (guards against silent changes)
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

from main import RECOMMENDED_WORDS, _compute_calibration, app, word_count

# ---------------------------------------------------------------------------
# Fixed essay texts (hardcoded, realistic TOEFL-style)
# ---------------------------------------------------------------------------

ESSAY_SHORT = (
    "I believe technology has improved our lives in many important ways. "
    "Communication is now faster and easier with smartphones and the internet. "
    "People can send messages instantly and make video calls around the world. "
    "Students benefit from online learning platforms and digital textbooks. "
    "For example, many universities offer free courses through online platforms. "
    "Healthcare has improved as doctors use advanced diagnostic tools and equipment. "
    "Telemedicine allows patients to consult doctors remotely without traveling. "
    "While some argue technology causes addiction, the benefits outweigh the drawbacks. "
    "Technology connects communities, improves education, and saves lives. "
    "In conclusion, technology has made our lives easier and will continue to do so. "
    "We should embrace these changes while being mindful of potential challenges. "
    "The positive impact of technology on society is clear and growing every year. "
    "Students especially benefit from the educational opportunities that technology provides. "
    "Communication across borders has never been more accessible or affordable than today."
)

ESSAY_MEDIUM = (
    "I strongly agree that technology has made our lives significantly easier. "
    "Communication has been revolutionized by smartphones and the internet. "
    "In the past, staying in touch required expensive phone calls or slow postal mail. "
    "Now we can instantly message, call, and video chat with anyone worldwide. "
    "This has strengthened both personal relationships and professional collaboration. "
    "Education has also been transformed by technology in many significant ways. "
    "Students have access to online courses, digital libraries, and interactive apps. "
    "For instance, platforms like Coursera and Khan Academy offer free quality education. "
    "During the pandemic, millions of students continued learning through video platforms. "
    "Without technology, continuing education would have been completely impossible. "
    "Healthcare has benefited enormously from technological advances in recent years. "
    "Modern diagnostic tools detect diseases earlier and more accurately than before. "
    "Telemedicine enables patients in remote areas to consult medical specialists easily. "
    "However, technology does bring some challenges that society must carefully address. "
    "Social media can lead to addiction and reduced face to face social interaction. "
    "The spread of misinformation online is also a growing concern for many communities. "
    "Despite these drawbacks, the advantages of technology clearly outweigh the disadvantages. "
    "Communication is faster, education is more accessible, and healthcare is vastly improved. "
    "As long as we use technology responsibly, it will remain a powerful force for good."
)

ESSAY_LONG = (
    "I strongly agree that technology has made our lives easier, and the evidence "
    "supporting this claim is overwhelming across multiple important domains. "
    "To begin with, communication has undergone a complete transformation in recent decades. "
    "In the past, people relied on postal services that took days or weeks to deliver. "
    "Today, we connect with anyone in the world instantly through messaging apps and email. "
    "Video conferencing has made face to face communication possible across continents. "
    "This has not only strengthened personal relationships but also facilitated global business. "
    "Furthermore, technology has fundamentally revolutionized the field of education. "
    "Students now have access to vast online libraries and interactive learning platforms. "
    "Platforms like Khan Academy and Coursera allow learners from any background to access "
    "high quality education completely free of charge, democratizing knowledge worldwide. "
    "During the pandemic, technology proved essential in keeping education alive through "
    "remote learning tools such as Zoom and Google Classroom, helping millions of students. "
    "In addition to communication and education, healthcare has benefited enormously "
    "from technological advances and innovations in medical science and practice. "
    "Modern diagnostic equipment can detect diseases at much earlier stages more accurately. "
    "Telemedicine allows patients in rural and underserved areas to consult specialists. "
    "Robotic surgery has increased precision in complex medical procedures significantly. "
    "Of course, technology is not without its downsides and potential negative effects. "
    "Social media can contribute to anxiety, cyberbullying, and the spread of misinformation. "
    "Excessive screen time may lead to health problems such as eye strain and poor posture. "
    "These are valid concerns that society must address through better digital literacy. "
    "In conclusion, despite certain challenges, the benefits of technology in communication, "
    "education, and healthcare far outweigh the drawbacks when used responsibly and thoughtfully."
)

# Compute and validate word counts at module level (fail-fast on bad test data)
_SHORT_WC = word_count(ESSAY_SHORT)
_MEDIUM_WC = word_count(ESSAY_MEDIUM)
_LONG_WC = word_count(ESSAY_LONG)

assert _SHORT_WC >= 120, f"ESSAY_SHORT has {_SHORT_WC} words, must be >= 120 (MIN_WORDS)"
assert _SHORT_WC < 220, f"ESSAY_SHORT has {_SHORT_WC} words, must be < 220 for penalty"
assert _MEDIUM_WC >= 120, f"ESSAY_MEDIUM has {_MEDIUM_WC} words, must be >= 120 (MIN_WORDS)"
assert _MEDIUM_WC < 220, f"ESSAY_MEDIUM has {_MEDIUM_WC} words, must be < 220 for penalty"
assert _LONG_WC >= 220, f"ESSAY_LONG has {_LONG_WC} words, must be >= 220 (RECOMMENDED_WORDS)"

# ---------------------------------------------------------------------------
# Mock LLM response (fixed subscores → deterministic raw_score)
# ---------------------------------------------------------------------------

RAW_SCORE = 24.0
SUBSCORES = {
    "task_response": 4.0, "coherence_cohesion": 4.0,
    "lexical_resource": 4.0, "grammar": 4.0,
}

MOCK_LLM = json.dumps({
    "estimated_score": RAW_SCORE,
    "subscores": SUBSCORES,
    "strengths": [
        {"label": "Clear position", "explanation": "Thesis is well stated.", "evidence": None}
    ],
    "weaknesses": [
        {
            "label": "Limited development", "explanation": "Ideas need more support.",
            "evidence": None,
            "evidence_reason": "Conceptual issue not tied to a single sentence.",
        }
    ],
    "top_fixes": ["Develop arguments", "Use varied vocabulary", "Add transitions"],
    "rewrite_first_paragraph": "Technology has profoundly transformed modern life.",
})


# ---------------------------------------------------------------------------
# Pure-function tests (no network, no API, no mocking)
# ---------------------------------------------------------------------------


class TestCalibrationConstant:
    """Guard test: RECOMMENDED_WORDS must be 220."""

    def test_recommended_words_is_220(self):
        assert RECOMMENDED_WORDS == 220


class TestEssayWordCounts:
    """Verify hardcoded essay word counts fall in expected ranges."""

    def test_short_word_count(self):
        assert 130 <= _SHORT_WC <= 170, f"ESSAY_SHORT: {_SHORT_WC} words"

    def test_medium_word_count(self):
        assert 170 <= _MEDIUM_WC < 220, f"ESSAY_MEDIUM: {_MEDIUM_WC} words"

    def test_long_word_count(self):
        assert 220 <= _LONG_WC <= 300, f"ESSAY_LONG: {_LONG_WC} words"


class TestCalibrationPureFunction:
    """Direct tests of _compute_calibration with known inputs."""

    def test_short_penalty_applied(self):
        cal = _compute_calibration(_SHORT_WC, RAW_SCORE)
        assert cal.length_factor < 1.0
        assert cal.calibrated_score < RAW_SCORE

    def test_medium_penalty_applied(self):
        cal = _compute_calibration(_MEDIUM_WC, RAW_SCORE)
        assert cal.length_factor < 1.0
        assert cal.calibrated_score < RAW_SCORE

    def test_long_no_penalty(self):
        cal = _compute_calibration(_LONG_WC, RAW_SCORE)
        assert cal.length_factor == 1.0
        assert cal.calibrated_score == RAW_SCORE

    @pytest.mark.parametrize("wc", [_SHORT_WC, _MEDIUM_WC, _LONG_WC])
    def test_formula_exact(self, wc):
        cal = _compute_calibration(wc, RAW_SCORE)
        expected_factor = round(min(1.0, wc / RECOMMENDED_WORDS), 4)
        expected_final = round(RAW_SCORE * min(1.0, wc / RECOMMENDED_WORDS), 1)
        expected_final = max(0.0, min(30.0, expected_final))
        assert cal.length_factor == expected_factor
        assert cal.calibrated_score == expected_final


# ---------------------------------------------------------------------------
# End-to-end tests via TestClient (mocked LLM)
# ---------------------------------------------------------------------------


class TestCalibrationEndToEnd:
    """Full pipeline tests: essay → mocked LLM → calibration → canonical response."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def _evaluate(self, client, essay_text):
        with patch("main._call_groq", return_value=MOCK_LLM):
            r = client.post(
                "/api/evaluate",
                json={"prompt": "Do you agree?", "essay": essay_text},
            )
        assert r.status_code == 200
        return r.json()

    def test_short_essay_penalized(self, client):
        data = self._evaluate(client, ESSAY_SHORT)
        assert data["scoring"]["length_penalty"] < 1.0
        assert data["scoring"]["final"] < data["scoring"]["raw"]
        assert data["overall_score"] == data["scoring"]["final"]

    def test_medium_essay_penalized(self, client):
        data = self._evaluate(client, ESSAY_MEDIUM)
        assert data["scoring"]["length_penalty"] < 1.0
        assert data["scoring"]["final"] < data["scoring"]["raw"]
        assert data["overall_score"] == data["scoring"]["final"]

    def test_long_essay_no_penalty(self, client):
        data = self._evaluate(client, ESSAY_LONG)
        assert data["scoring"]["length_penalty"] == 1.0
        assert data["scoring"]["final"] == data["scoring"]["raw"]
        assert data["overall_score"] == data["scoring"]["raw"]

    def test_exact_calibration_values(self, client):
        """Verify precise calibrated scores match the deterministic formula."""
        for essay, label in [
            (ESSAY_SHORT, "short"),
            (ESSAY_MEDIUM, "medium"),
            (ESSAY_LONG, "long"),
        ]:
            data = self._evaluate(client, essay)
            wc = data["text_stats"]["word_count"]
            raw = data["scoring"]["raw"]
            expected_factor = round(min(1.0, wc / RECOMMENDED_WORDS), 4)
            expected_final = round(raw * min(1.0, wc / RECOMMENDED_WORDS), 1)
            expected_final = max(0.0, min(30.0, expected_final))
            assert data["scoring"]["length_penalty"] == expected_factor, f"{label}: length_penalty"
            assert data["scoring"]["final"] == expected_final, f"{label}: final"
            assert data["overall_score"] == expected_final, f"{label}: overall_score"
