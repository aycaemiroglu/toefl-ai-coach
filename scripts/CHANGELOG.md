# CHANGELOG - generate_essays.py Refactor

## Changes Applied

### A) Deterministic Seeding
- **Change**: Replaced `hash(level) % 1000` with fixed level offsets (B1=101, B2=202, C1=303) and formula `base_seed + prompt_idx * 100 + level_offset`
- **Reason**: `hash()` is non-deterministic across Python versions and runs. Fixed offsets guarantee identical style constraints for same seed.
- **Impact**: Same `--seed` value now produces identical style constraints (stance, example_count, rhetorical_style) for each essay.

### B) Fixed Dry-Run Word Padding
- **Change**: Replaced space padding with real filler sentences from a predefined list. Added logic to calculate words per example and pad with actual sentences.
- **Reason**: Space padding doesn't increase `word_count`. Real sentences ensure placeholder essays meet target word counts realistically.
- **Impact**: Dry-run essays now have accurate word counts matching their level's target range.

### C) Enforce Word Range on Real Generations
- **Change**: Added word count validation after generation. If out of range, retry up to 2 additional times with stronger word range enforcement in system prompt.
- **Reason**: Generated essays sometimes fall outside target word ranges. Automatic retry with emphasis improves compliance.
- **Impact**: Better adherence to word count requirements, with logging when retries occur.

### D) Stronger "Essay-Only" Output Enforcement
- **Change**: Added `has_meta_text()` function with regex patterns to detect titles, bullets, numbered lists, and meta-commentary. Retry generation if detected (bounded).
- **Reason**: Models sometimes include non-essay content. Detection + retry is more robust than brittle string stripping.
- **Impact**: Cleaner essay outputs with fewer formatting artifacts.

### E) OpenAI Client Import Cleanup
- **Change**: Changed from `import openai` to `from openai import OpenAI, APIError, RateLimitError`. Updated exception handling to use imported names.
- **Reason**: More explicit imports improve code clarity and compatibility with OpenAI package structure.
- **Impact**: Cleaner imports, same functionality.

### F) Added `--max-tokens` CLI Argument
- **Change**: Added `--max-tokens` argument with default 1200. Replaced hardcoded `max_tokens=1200` in API calls.
- **Reason**: Allows users to adjust token limits for different models or use cases.
- **Impact**: More flexible configuration without code changes.

## Additional Improvements

- Added `seed_offset` field to `LEVEL_SPECS` for deterministic seeding
- Enhanced `build_system_prompt()` with `enforce_word_range` parameter for retries
- Improved `clean_essay_text()` as fallback when retries are exhausted
- Added progress logging for word range retries and meta-text detection
- Updated main loop to use `get_essay_seed()` for deterministic per-essay seeds
