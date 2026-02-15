# Connecting FastAPI Backend to the Frontend

How to wire a FastAPI TOEFL essay evaluator to a lightweight frontend for visualization, and why the design supports interpretability and portfolio value.

---

## Request/Response Flow

1. **User:** Selects a TOEFL prompt and pastes an essay in the frontend (`frontend/` React app).
2. **Frontend:** On "Analyze Essay", sends **POST** to the backend (e.g. `/writing/feedback` or `/analyze`) with a JSON body: `{ "prompt": "<essay topic>", "essay": "<user text>" }`.
3. **Backend (FastAPI):** Receives the body, calls the LLM (e.g. Groq) with a fixed system prompt + the given prompt and essay, and returns a JSON response (e.g. `{ "model": "...", "feedback": "..." }` or structured fields like `score`, `strengths`, `weaknesses`).
4. **Frontend:** Renders the response (feedback text and optional model name) in a clear, readable block so the user sees exactly what the AI returned.

For local development, run the FastAPI server (e.g. port 8000) and either point the frontend at `http://localhost:8000` or use Vite’s proxy so requests to `/writing` go to the backend. No CORS issues if the frontend is served from the same origin or the proxy forwards correctly.

---

## Why JSON Structure Matters for Interpretability

- **Stable contract:** A fixed request schema (`prompt`, `essay`) and response schema (e.g. `model`, `feedback`, or `score` / `strengths` / `weaknesses` / `suggestions`) make it clear what the system expects and what it returns. Reviewers and users can replicate calls and inspect inputs/outputs without guessing.
- **Structured feedback:** Returning separate fields (e.g. `strengths`, `weaknesses`, `suggestions`) instead of one long string lets the UI show each dimension in its own section. That makes it easier to see whether the model’s reasoning is consistent (e.g. score vs. listed weaknesses) and to audit quality.
- **Model and provenance:** Including `model` (and optionally `prompt_tokens`, `completion_tokens`) in the response documents which system produced the feedback and at what cost, which supports reproducibility and transparency in a research or portfolio context.

---

## How This Demonstrates Applied AI Skills in a Portfolio

- **End-to-end pipeline:** You show you can go from user input → API → LLM call → structured output → visualization, not just a notebook or script.
- **API design:** Defining a minimal, consistent JSON API and documenting it shows you think about integration and maintainability.
- **Interpretability and transparency:** By exposing the same prompt and essay you send to the model and rendering the exact feedback (and optionally score/strengths/weaknesses), you demonstrate that you care about explainability and auditability of AI outputs.
- **Stack choices:** FastAPI + React frontend is a common, professional setup that signals you can build deployable demos and collaborate with frontend or full-stack workflows.

Use this section in your main README or in `docs/`; adjust endpoint names and field names to match your actual FastAPI routes and response schema.

---

## README-ready summary (copy-paste)

**Connecting backend and frontend**

- **Flow:** User selects a prompt and enters an essay → frontend POSTs `{ "prompt", "essay" }` to the FastAPI backend → backend calls the LLM and returns JSON (e.g. `{ "model", "feedback" }` or structured `score` / `strengths` / `weaknesses`) → frontend renders the result.
- **Why JSON:** A fixed request/response schema makes the API reproducible and auditable; structured fields (e.g. strengths vs. weaknesses) improve interpretability by letting the UI show each dimension clearly.
- **Portfolio value:** The demo shows an end-to-end applied AI pipeline (input → API → LLM → structured output → UI), clear API design, and a focus on transparency (same prompt/essay and visible feedback).
