# TOEFL AI Coach

AI-powered TOEFL tools: automated essay scoring, prompting experiments, and synthetic data (Groq). Extensible for other sections.

---

## Quick start

### 1. Environment (once)

```bash
cd toefl-ai-coach
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file with your Groq API key:

```
GROQ_API_KEY=gsk_your_key_here
```

### 2. What you can run

| Goal | Command | Notes |
|------|--------|------|
| **Backend (FastAPI)** | `uvicorn backend.main:app --reload --port 8000` | Run in venv; needs GROQ_API_KEY in `.env` |
| **React frontend** | `cd frontend && npm install && npm run dev` | Needs backend on port 8000; opens http://localhost:3000 |
| **Synthetic essay generation** (30 essays) | `python scripts/generate_essays.py` | Uses Groq API; `--dry-run` for mock |
| **Offline evaluation harness** | `python -m eval_harness -i data/essays -o results` | Batch-scores essays; produces JSONL + summary |

### 3. Synthetic essays (scripts)

```bash
source .venv/bin/activate
python scripts/generate_essays.py
```

- **Test without API:** `python scripts/generate_essays.py --dry-run`
- **Reproducible:** `python scripts/generate_essays.py --seed 42`
- **Overwrite files:** `python scripts/generate_essays.py --overwrite`

Output: `data/essays/` (JSON + TXT per essay).

### 4. Backend (FastAPI)

```bash
source .venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Runs on http://localhost:8000. Requires `GROQ_API_KEY` in `.env` (or `backend/.env`).

- **Health check:** http://localhost:8000/health
- **API docs:** http://localhost:8000/docs (Swagger UI)

### 5. React frontend

```bash
cd frontend
npm install
npm run dev
```

Opens http://localhost:3000. Requests to `/api/evaluate` are proxied to `http://localhost:8000` (see `frontend/vite.config.ts`). **Start the backend first** (step 4) so the "Analyze Essay" button returns real feedback.

---

## Project structure

```
toefl-ai-coach/
├── backend/        # FastAPI app (main.py, requirements.txt)
├── data/           # Essay templates, generated data (data/essays/ ignored)
├── docs/           # Design and integration notes
├── frontend/       # React app (Vite) for writing feedback UI
├── eval_harness/   # Offline batch evaluation (CLI + report)
├── results/        # Experiment outputs (ignored)
├── scripts/        # generate_essays.py, etc.
├── .env             # GROQ_API_KEY (create locally, do not commit)
├── requirements.txt
└── README.md
```

---

## How to run offline evaluation

The evaluation harness runs every essay in a folder through the **same `evaluate_essay_core` function** used by the FastAPI endpoint — no duplicated logic.

### Basic usage

```bash
source .venv/bin/activate
python -m eval_harness --input data/essays --out results
```

### CLI options

| Flag | Description |
|------|-------------|
| `--input`, `-i` | Directory containing `.txt` and/or `.json` essay files (required) |
| `--out`, `-o` | Output directory for `results.jsonl` and `summary.md` (default: `results`) |
| `--seed`, `-s` | Random seed for deterministic runs |
| `--delay`, `-d` | Seconds between LLM calls to avoid rate-limits (default: 0) |
| `--verbose`, `-v` | Enable debug-level logging |

### Input formats

- **`.txt`** — entire file is the essay text; uses a default prompt.
- **`.json`** — must contain an `"essay"` field; optionally `"prompt"`, `"prompt_id"`, `"level"`.

### Outputs

| File | Contents |
|------|----------|
| `results/results.jsonl` | One JSON object per essay — full evaluation response including `essay_text`, scoring, confidence, evidence, and `_meta` (source file, level) |
| `results/summary.md` | Aggregated report: length tier distribution, raw vs calibrated averages, calibration impact buckets, confidence distribution by tier, evidence quality (strengths + weaknesses + substring verification), top 10 weakness labels |

### Example

```bash
# Deterministic run with 1s delay between API calls
python -m eval_harness -i data/essays -o results --seed 42 --delay 1 -v
```

---

## Evaluation Pipeline Improvements & Design Decisions

This section documents the major scoring and feedback improvements in the evaluation pipeline, explaining not just **what** was implemented but **why** each decision was made.

### 1. Separation of Content Quality and Test Compliance

The system deliberately separates **writing quality assessment** from **test format compliance** (such as essay length). The LLM evaluates only content quality using four rubric-based subscores:

| Subscore | What it measures |
|---|---|
| Task Response | Addresses the prompt, takes a clear position, develops ideas |
| Coherence & Cohesion | Logical flow, paragraph structure, transitions |
| Lexical Resource | Vocabulary range, precision, collocations |
| Grammar | Sentence variety, accuracy, complexity |

Each subscore is rated 0–5. The server computes a **raw score (0–30)** from these subscores. This raw score reflects *content quality only*, independent of essay length.

**Rationale:**
- Prevents penalizing strong writing solely due to format issues like length.
- Allows clearer, more actionable diagnostic feedback — a student can see that their *writing* is strong even if the essay is too short.
- Keeps LLM evaluation focused on what it does well (qualitative language analysis) while deferring quantitative adjustments to deterministic server-side logic.

### 2. Smooth Length-Based Score Calibration

TOEFL Independent Writing expects responses of approximately 250–300 words. Short essays tend to receive overly generous scores from LLMs because the model evaluates *what is written* without sufficiently penalizing *what is missing*.

To address this, a smooth, deterministic calibration function is applied **server-side** after the LLM returns its evaluation:

```
length_factor = min(1.0, word_count / 220)
calibrated_score = round(raw_score × length_factor, 1)
calibrated_score = clamp(calibrated_score, 0, 30)
```

| Word count | length_factor | Effect on a raw score of 26 |
|---|---|---|
| 250+ | 1.0 | 26.0 (no change) |
| 220 | 1.0 | 26.0 (no change) |
| 200 | 0.91 | 23.6 |
| 150 | 0.68 | 17.7 |
| 120 | 0.55 | 14.2 |

Key properties:
- **Subscores are never modified.** The student sees the same rubric feedback regardless of length.
- **The function is continuous and monotonic** — no abrupt thresholds or cliffs.
- **220 words is the breakpoint** (essays at or above this length receive the full raw score).
- The `calibration` object in the API response provides full transparency: `raw_score`, `length_factor`, `calibrated_score`, and a human-readable `note`.

**Rationale:**
- LLMs consistently over-score short essays because they evaluate surface-level quality without penalizing insufficient development.
- A multiplicative factor (rather than a fixed deduction) ensures the penalty is proportional — a mediocre short essay is not penalized as harshly as a high-scoring short essay, which is the correct behavior.
- Transparency is preserved: the frontend shows both the raw and calibrated scores so students understand *why* their score was adjusted.

### 3. Length Evaluation Tiers

To improve interpretability, the system classifies each essay into one of three length tiers and provides a clear, deterministic message:

| Tier | Word count | Message |
|---|---|---|
| **short** | < 220 | "Below recommended length; score calibrated." |
| **recommended** | 220–249 | "Meets recommended length; full score applied." |
| **ideal** | ≥ 250 | "Ideal length range; maximum confidence." |

This message is displayed directly under the overall score in the UI. It uses neutral, informational styling (not warning/error) to guide the student without causing alarm.

**Rationale:**
- Students need to understand the *relationship* between length and score at a glance.
- A single sentence is more actionable than raw numbers — "Below recommended length; score calibrated" immediately tells the student what to do next.
- The tiers align with the calibration math but are expressed in plain language.

### 4. Server-Side Confidence Estimation

Confidence is computed entirely server-side using deterministic heuristics. The LLM is explicitly instructed **not** to generate confidence scores, because LLMs tend to output uniformly high confidence regardless of actual reliability.

The confidence score (0–100, mapped to Low/Medium/High) is reduced by penalty rules:

| Factor | Penalty | Condition |
|---|---|---|
| Very short essay | −35 | word_count < 180 |
| Short essay | −20 | 180 ≤ word_count < 220 |
| Slightly short essay | −10 | 220 ≤ word_count < 250 |
| High subscore variance | −20 | max − min subscore ≥ 3 |
| Moderate subscore variance | −10 | max − min subscore = 2 |
| High score + short essay | −20 | score ≥ 25 and word_count < 220 |
| High score + very short essay | −15 | score ≥ 23 and word_count < 180 |
| Many weaknesses + high score | −15 | weaknesses ≥ 3 and score ≥ 25 |
| Missing counterargument | −10 | counterargument weakness + task_response ≥ 4 |
| Calibration reduced score | −10 | word_count < 220 and calibration_delta ≥ 2 |

The result includes:
- `level`: High (≥ 80), Medium (≥ 50), or Low (< 50)
- `numeric_score`: 0–100
- `reasons`: human-readable list explaining each penalty
- `signals`: raw diagnostic values for debugging

**Rationale:**
- LLMs are unreliable at self-assessing confidence — they default to high confidence even on edge cases.
- Multiple penalty factors create a nuanced signal: a short essay with balanced subscores gets a different confidence than a short essay with wildly varying subscores.
- The `reasons` list makes confidence explainable, not a black box.
- Calibration-awareness prevents double-counting: if the score was already reduced by length calibration, the confidence system notes the additional uncertainty without re-applying the same penalty.

### 5. Evidence Validation and Server-Side Overrides

Weakness feedback includes optional `evidence` fields — exact quotes from the student's essay. These are validated server-side:

- Evidence must be an **exact verbatim substring** of the essay (smart quotes normalized).
- Evidence is capped at **25 words** to keep quotes focused.
- If the LLM returns evidence that fails validation, it is set to `null` with an `evidence_reason` explaining why.
- For **lexical weaknesses** (repetition, limited vocabulary), the server runs its own analysis: it finds repeated content words, identifies the most representative sentence, and overrides the LLM's null evidence when possible.

**Rationale:**
- LLMs frequently paraphrase or fabricate quotes rather than copying exact substrings.
- Server-side validation prevents misleading feedback — students should only see quotes that actually appear in their essay.
- The lexical override compensates for a known LLM blind spot: models struggle to identify specific repetition examples but are good at detecting the *pattern* of repetition.

### 6. Pipeline Summary

```
Essay submitted
    │
    ▼
┌─────────────────────────┐
│  LLM Evaluation         │  Qualitative: subscores, strengths,
│  (Groq / llama-3.1-8b)  │  weaknesses, top_fixes, rewrite
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Evidence Validation     │  Exact substring check, lexical override
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Length Calibration       │  length_factor = min(1, wc / 220)
│  (deterministic)         │  calibrated_score = raw × factor
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Length Evaluation        │  Tier: short / recommended / ideal
│  (deterministic)         │  Human-readable message
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Confidence Estimation   │  Multi-factor heuristic (0–100)
│  (deterministic)         │  Aware of calibration delta
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  API Response            │  estimated_score = calibrated
│                          │  + calibration, length_evaluation,
│                          │    confidence, subscores, feedback
└─────────────────────────┘
```

### Confidence Sanity Checks

Expected behavior for spot-checking:

- **Short essay (~160 words)** → Low or Medium at most
- **Long essay (~280 words)** → Medium or High (depending on variance)
- **Subscores differ by 3+ points** → Not High
- **Score ≥ 26 with word_count < 200** → Must not be High
- **Essay ≥ 220 words, balanced subscores** → High

To debug confidence computation, set `DEBUG_CONFIDENCE=true` in `.env` and check backend logs.

---

## Contact

Ayça Emiroğlu | ayca.emiroglu23@gmail.com

## License

MIT License
