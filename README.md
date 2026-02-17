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
├── results/        # Experiment outputs (ignored)
├── scripts/        # generate_essays.py, etc.
├── .env             # GROQ_API_KEY (create locally, do not commit)
├── requirements.txt
└── README.md
```

---

## Confidence sanity checks

The backend computes confidence server-side (LLM does not generate it). Expected behavior:

- **Short essay (~160 words)** → Low or Medium at most
- **Long essay (~280 words)** → Medium/High (depending on variance)
- **Subscores differ by 3+ points** → Not High
- **Score ≥ 26 with word_count < 200** → Must not be High

To debug confidence computation, set `DEBUG_CONFIDENCE=true` in `.env` and check backend logs.

---

## Contact

Ayça Emiroğlu | ayca.emiroglu23@gmail.com

## License

MIT License
