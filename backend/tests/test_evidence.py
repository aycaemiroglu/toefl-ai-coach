"""
Evidence validation tests.

Protects against:
- Evidence strings that are not exact substrings of the original essay
- Items with null evidence but missing evidence_fallback
- Items with both evidence AND evidence_fallback set (should be mutually exclusive)
"""


def _normalize_quotes(s: str) -> str:
    """Mirror the backend's smart-quote normalization for fair comparison."""
    return (
        s.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )


class TestStrengthEvidence:
    def test_evidence_is_substring_of_essay(self, evaluate_result):
        """Every non-null strength evidence must appear verbatim in the essay."""
        _, data, essay_text = evaluate_result
        norm_essay = _normalize_quotes(essay_text)
        for s in data["evidence"]["strengths"]:
            if s["evidence"] is not None:
                norm_ev = _normalize_quotes(s["evidence"])
                assert norm_ev in norm_essay, (
                    f"Strength evidence not found in essay: {s['evidence']!r}"
                )


class TestWeaknessEvidence:
    def test_evidence_is_substring_of_essay(self, evaluate_result):
        """Every non-null weakness evidence must appear verbatim in the essay."""
        _, data, essay_text = evaluate_result
        norm_essay = _normalize_quotes(essay_text)
        for w in data["evidence"]["weaknesses"]:
            if w["evidence"] is not None:
                norm_ev = _normalize_quotes(w["evidence"])
                assert norm_ev in norm_essay, (
                    f"Weakness evidence not found in essay: {w['evidence']!r}"
                )

    def test_null_evidence_has_fallback(self, evaluate_result):
        """If evidence is null, evidence_fallback must be a non-empty string."""
        _, data, _ = evaluate_result
        for w in data["evidence"]["weaknesses"]:
            if w["evidence"] is None:
                fallback = w.get("evidence_fallback")
                assert fallback and isinstance(fallback, str) and fallback.strip(), (
                    f"Weakness '{w['label']}' has null evidence but no evidence_fallback"
                )

    def test_no_evidence_and_fallback_simultaneously(self, evaluate_result):
        """Evidence and evidence_fallback should be mutually exclusive."""
        _, data, _ = evaluate_result
        for w in data["evidence"]["weaknesses"]:
            if w["evidence"] is not None:
                assert w.get("evidence_fallback") is None, (
                    f"Weakness '{w['label']}' has both evidence and evidence_fallback"
                )
