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
