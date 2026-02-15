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
| **Synthetic essay generation** (30 essays) | `python scripts/generate_essays.py` | Uses Groq API; `--dry-run` for mock |
| **React frontend** | `cd frontend && npm install && npm run dev` | Needs backend on port 8000 for `/writing/feedback` (or use Vite proxy) |

### 3. Synthetic essays (scripts)

```bash
source .venv/bin/activate
python scripts/generate_essays.py
```

- **Test without API:** `python scripts/generate_essays.py --dry-run`
- **Reproducible:** `python scripts/generate_essays.py --seed 42`
- **Overwrite files:** `python scripts/generate_essays.py --overwrite`

Output: `data/essays/` (JSON + TXT per essay).

### 4. React frontend

```bash
cd frontend
npm install
npm run dev
```

Opens http://localhost:3000. Requests to `/writing/feedback` are proxied to `http://localhost:8000` by default (see `frontend/vite.config.js`). Start your FastAPI (or other) backend on port 8000 so the button returns real feedback.

---

## Project structure

```
toefl-ai-coach/
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

## Contact

Ayça Emiroğlu | ayca.emiroglu23@gmail.com

## License

MIT License
