# TOEFL Essay Evaluator (FastAPI + Groq)

## Setup and run

From the project root:

```bash
# Create venv (once)
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install backend deps
pip install -r backend/requirements.txt

# Copy env and set your Groq key
cp backend/.env.example backend/.env
# Edit backend/.env and set GROQ_API_KEY=...

# Run the API on port 8000
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

From inside `backend/`:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set GROQ_API_KEY in .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- **Health:** `GET http://localhost:8000/health`
- **Evaluate:** `POST http://localhost:8000/api/evaluate` with JSON `{"prompt": "...", "essay": "..."}`

## Running Tests

All tests mock the LLM call, so no API key or network access is needed.

```bash
cd backend
pytest -q               # quick summary
pytest -v               # verbose, one line per test
pytest tests/test_contract.py       # only contract/schema tests
pytest tests/test_invariants.py     # only scoring/confidence invariants
pytest tests/test_evidence.py       # only evidence validation
pytest tests/test_golden.py         # only golden/snapshot tests
```

### Test Structure

```
tests/
  conftest.py           # shared fixtures: TestClient, mock wiring, parametrized essays
  fixtures/
    essays.json         # 3 essay tiers (short/recommended/ideal) + deterministic LLM responses
  golden/
    short.json          # snapshot of expected API output (dynamic fields stripped)
    recommended.json
    ideal.json
  test_contract.py      # schema validation, required keys, field ranges, backward-compat
  test_invariants.py    # calibration math, confidence heuristic guarantees
  test_evidence.py      # evidence substring checks, evidence_reason mutuality
  test_golden.py        # full response snapshot comparison
  test_main.py          # unit tests for internal helpers (word_count, calibration, etc.)
  update_golden.py      # CLI helper to regenerate golden files
```

### Updating Golden Files

After an **intentional** contract change, regenerate golden snapshots:

```bash
cd backend
python -m tests.update_golden
```

Then review the diff and commit the updated golden files.

## Offline Evaluation Harness

Run the evaluator on a folder of essays and produce a metrics report — same
pipeline as the API, no server needed.

### Input Formats

Place files in a folder (e.g. `data/essays/`):

- **`.txt`** — plain essay text (uses a default prompt)
- **`.json`** — `{"essay": "...", "prompt": "...", "prompt_id": "...", "level": "..."}`  
  Only `essay` is required; others are optional metadata.

### Running

```bash
# From project root:
python -m eval_harness --input data/essays --out results

# With rate-limit throttle (recommended for large batches):
python -m eval_harness --input data/essays --out results --delay 5

# Deterministic seed + verbose logging:
python -m eval_harness -i data/essays -o results --seed 42 -v
```

### Output

| File | Description |
|------|-------------|
| `results/results.jsonl` | One JSON object per essay (full API-equivalent response + `_meta`) |
| `results/summary.md` | Aggregated metrics report |

### Summary Report Contents

- Length tier distribution (short / recommended / ideal)
- Average raw vs. calibrated score
- Average confidence score by tier
- Calibration impact distribution
- Evidence quality (% weaknesses with substring evidence vs. null)
- Top 10 most common weakness labels
- Error log (if any essays failed)
