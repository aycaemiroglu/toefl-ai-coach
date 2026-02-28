I am working on a TOEFL Writing Evaluation project focused on downstream reliability rather than model training.

Project goal:
Build a robust AI-assisted TOEFL essay evaluator that produces calibrated, interpretable, and trustworthy scores — not just raw LLM outputs.

Core architecture:

- Upstream: LLM evaluates essays using a TOEFL-style rubric (task response, coherence, lexical resource, grammar).
- Downstream (primary focus):
    - Deterministic calibration based on essay length.
    - Confidence scoring based on multiple signals.
    - Stable, machine-readable JSONL output for batch analysis.
    - Summary reports aggregating results across essays.

Key design decisions:

1. Raw vs calibrated scores are explicitly separated.
    - raw_score_30: model output (0–30)
    - calibrated_score_30: raw_score adjusted by length_factor
    - overall_score = calibrated_score_30 (single source of truth)
2. Length-based calibration:
    - length_factor = min(1, word_count / 220)
    - adjusted_score = round(raw_score * length_factor, 1)
3. Confidence scoring (computed server-side only, never by the LLM):
Signals include:
    - Word count penalty
    - Subscore variance
    - High-score + short-essay mismatch
    - Weakness–score inconsistency
    Output:
    {
    level: Low | Medium | High,
    numeric_score_0_100,
    reasons[],
    signals{}
    }
4. Schema design:
    - Canonical schema only (aliases removed to avoid ambiguity).
    - Single source of truth for each concept.
    - Output stored in JSONL (one JSON object per line) for robustness.
    - Fields include: overall_score, scoring{}, rubric{}, confidence{}.
5. Harness & evaluation:
    - Batch processing of essays.
    - Results written to results.jsonl.
    - Summary report includes:
        - Length tier distribution (short / recommended / ideal)
        - Raw vs calibrated averages
        - Calibration impact buckets
        - Confidence distribution
6. Testing strategy:
    - Contract tests: canonical fields exist, aliases do not.
    - Regression tests: short vs medium vs ideal essays.
    - JSONL parse tests.
    - No scoring logic changes during refactors.
7. Engineering practices:
    - Feature branches + PRs even as a solo developer.
    - Explicit migration notes.
    - Deterministic downstream logic to stabilize stochastic LLM output.

Current state:

- Schema refactored to remove aliases.
- Length calibration and confidence logic implemented.
- Harness summary output validated for consistency.
- Project positioned for portfolio + graduate study applications.

When continuing:

- Assume all of the above context is active.
- Do NOT reintroduce aliases unless explicitly requested.
- Focus on clarity, reliability, and interview-ready explanations.
