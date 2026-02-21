"""
Invariant tests for scoring, calibration, and confidence.

Protects against:
- length_penalty != 1 when word_count >= 220
- final score > raw score
- overall_score != scoring.final
- Confidence being "High" for very short essays
- Confidence being "Low" for ideal essays with balanced subscores
"""


class TestCalibrationInvariants:
    """Scoring calibration must follow length_penalty = min(1, wc / 220)."""

    def test_length_penalty_one_when_long_enough(self, evaluate_result, essay_key):
        _, data, _ = evaluate_result
        wc = data["text_stats"]["word_count"]
        if wc >= 220:
            assert data["scoring"]["length_penalty"] == 1.0
            assert data["scoring"]["final"] == data["scoring"]["raw"]

    def test_final_le_raw_when_short(self, evaluate_result, essay_key):
        _, data, _ = evaluate_result
        wc = data["text_stats"]["word_count"]
        if wc < 220:
            assert data["scoring"]["final"] <= data["scoring"]["raw"]
            assert data["scoring"]["length_penalty"] < 1.0

    def test_overall_score_is_scoring_final(self, evaluate_result):
        """overall_score must always equal scoring.final."""
        _, data, _ = evaluate_result
        assert data["overall_score"] == data["scoring"]["final"]

    def test_length_tier_matches_word_count(self, evaluate_result):
        _, data, _ = evaluate_result
        wc = data["text_stats"]["word_count"]
        tier = data["length"]["tier"]
        if wc < 220:
            assert tier == "short"
        elif wc < 250:
            assert tier == "recommended"
        else:
            assert tier == "ideal"


class TestConfidenceInvariants:
    """Confidence heuristic must respect length and variance signals."""

    def test_very_short_essay_not_high(self, evaluate_result):
        """Essays under 180 words should never have High confidence."""
        _, data, _ = evaluate_result
        wc = data["text_stats"]["word_count"]
        if wc < 180:
            assert data["confidence"]["level"] != "High", (
                f"word_count={wc} but confidence is High"
            )

    def test_ideal_balanced_at_least_medium(self, evaluate_result):
        """
        An ideal-length essay with low subscore variance and few weaknesses
        should not be Low confidence.
        """
        _, data, _ = evaluate_result
        wc = data["text_stats"]["word_count"]
        rubric_vals = [
            data["rubric"]["task_response"],
            data["rubric"]["coherence"],
            data["rubric"]["lexical"],
            data["rubric"]["grammar"],
        ]
        variance = max(rubric_vals) - min(rubric_vals)
        weakness_count = len(data["evidence"]["weaknesses"])
        if wc >= 250 and variance <= 1 and weakness_count <= 2:
            assert data["confidence"]["level"] in ("Medium", "High"), (
                f"Ideal essay (wc={wc}, var={variance}, wk={weakness_count}) "
                f"got confidence={data['confidence']['level']}"
            )

    def test_confidence_reasons_nonempty(self, evaluate_result):
        _, data, _ = evaluate_result
        assert len(data["confidence"]["reasons"]) >= 1

    def test_confidence_signals_word_count_matches(self, evaluate_result):
        _, data, _ = evaluate_result
        assert data["confidence"]["signals"]["word_count"] == data["text_stats"]["word_count"]
