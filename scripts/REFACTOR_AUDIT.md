# Refactor Self-Audit Report

## A) Deterministic Seeding

### Potential Pitfalls
- **Risk**: Fixed offsets might collide if prompt count exceeds 100. **Mitigation**: Using `prompt_idx * 100` ensures 100 prompts before collision, sufficient for 10 prompts.
- **Risk**: Seed formula must be consistent across runs. **Mitigation**: Formula is pure arithmetic with fixed constants, guaranteed deterministic.
- **Verification**: Run `--dry-run --seed 42` twice, compare `p01_b1.txt` content - should be identical.

### How I Verify
1. Run script twice with same seed, compare first essay content (should match).
2. Check that different prompts/levels produce different style constraints (seed values differ).
3. Verify seed formula: `base_seed + prompt_idx * 100 + level_offset` produces unique values.

---

## B) Fix Dry-Run Word Padding

### Potential Pitfalls
- **Risk**: Filler sentences might create repetitive text. **Mitigation**: Using modulo indexing cycles through sentences, adds variety.
- **Risk**: Word count calculation might be off if sentences are trimmed incorrectly. **Mitigation**: Final trim uses `split()[:target_words]` which is safe.
- **Verification**: Run `--dry-run`, check JSON `word_count` fields - all should be within target ranges.

### How I Verify
1. Generate dry-run essays, extract word counts from JSON files.
2. Verify all counts are within level-specific ranges (B1: 220-250, etc.).
3. Check that padding actually increases word count (not just spaces).

---

## C) Enforce Word Range on Real Generations

### Potential Pitfalls
- **Risk**: Infinite retry loop if model consistently fails. **Mitigation**: Bounded retries (`word_range_retries=2`), fails after total attempts.
- **Risk**: Stronger prompt might not help if model ignores it. **Mitigation**: Logs retry attempts, fails gracefully with clear error message.
- **Verification**: Run real generation, check logs for "Word count out of range" messages, verify final essays are in range.

### How I Verify
1. Generate essays with API, check for retry messages in output.
2. Verify final word counts in JSON files are within ranges.
3. Test edge case: if model consistently fails, should error after bounded retries.

---

## D) Stronger "Essay-Only" Output Enforcement

### Potential Pitfalls
- **Risk**: Regex patterns might false-positive on valid essay content. **Mitigation**: Patterns check first 3 lines only, common meta-text patterns are specific.
- **Risk**: Retry might not help if model is trained to include titles. **Mitigation**: Bounded retries, fallback to `clean_essay_text()` on final attempt.
- **Verification**: Manually test with essays containing meta-text patterns, verify detection and retry behavior.

### How I Verify
1. Check that `has_meta_text()` detects common patterns (Title:, Essay:, bullets).
2. Verify retry logic triggers on detection (check logs).
3. Test that clean fallback works if retries exhausted.

---

## E) OpenAI Client Import Cleanup

### Potential Pitfalls
- **Risk**: Exception names might differ across OpenAI package versions. **Mitigation**: Using `openai.RateLimitError` and `openai.APIError` (standard names).
- **Risk**: Import structure might change. **Mitigation**: Kept both `from openai import OpenAI` and `import openai` for exceptions (compatible pattern).
- **Verification**: Script compiles, exception handling unchanged functionally.

### How I Verify
1. Syntax check passes (`python3 -m py_compile`).
2. Exception handling code unchanged (same logic, cleaner imports).
3. Compatible with OpenAI package versions that support `OpenAI` class.

---

## F) Add `--max-tokens` CLI Argument

### Potential Pitfalls
- **Risk**: Default might be too low for some models. **Mitigation**: Default 1200 is safe for 320 words, user can override.
- **Risk**: Very low values might truncate essays. **Mitigation**: User responsibility, but default is conservative.
- **Verification**: Test with different `--max-tokens` values, verify it's passed to API calls.

### How I Verify
1. Run with `--max-tokens 800`, check output shows correct value.
2. Verify argument is passed to `client.chat.completions.create(max_tokens=...)`.
3. Test that default (1200) works if argument omitted.

---

## Overall Risk Assessment

**Low Risk Changes:**
- A (deterministic seeding): Pure arithmetic, no side effects
- E (import cleanup): Cosmetic, same functionality
- F (CLI arg): Additive, backward compatible

**Medium Risk Changes:**
- B (word padding): Logic change but dry-run only, easy to verify
- C (word range enforcement): Adds retry logic, bounded and logged
- D (meta-text detection): Pattern matching, bounded retries with fallback

**Mitigation Strategy:**
- All changes preserve CLI interface (backward compatible)
- Bounded retries prevent infinite loops
- Comprehensive logging for debugging
- Dry-run mode allows testing without API costs

---

## Testing Priority

1. **Critical**: Dry-run deterministic seeding (A) - ensures reproducibility
2. **High**: Word count validation (B, C) - core functionality
3. **Medium**: Meta-text detection (D) - quality improvement
4. **Low**: Import cleanup (E), CLI arg (F) - cosmetic/optional
