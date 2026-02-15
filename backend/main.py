"""
Minimal FastAPI backend for TOEFL essay evaluation via Groq (OpenAI-compatible API).
"""
import json
import os
import re
import time
from typing import Any

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field

# Load .env from backend/ when running as e.g. uvicorn backend.main:app
load_dotenv()
load_dotenv(Path(__file__).resolve().parent / ".env")

# --- Config ------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
MIN_WORDS = 150

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is required. Set it in .env or environment.")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
)

# --- Pydantic models ---------------------------------------------------------


class EvaluateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    essay: str = Field(..., min_length=1)


class Subscores(BaseModel):
    task_response: float = Field(..., ge=0, le=5)
    coherence_cohesion: float = Field(..., ge=0, le=5)
    lexical_resource: float = Field(..., ge=0, le=5)
    grammar: float = Field(..., ge=0, le=5)


class EvaluateResponse(BaseModel):
    model: str
    estimated_score: float = Field(..., ge=0, le=30)
    subscores: Subscores
    strengths: list[str]
    weaknesses: list[str]
    top_fixes: list[str] = Field(..., min_length=3, max_length=3)
    rewrite_first_paragraph: str
    word_count: int
    latency_ms: int


# --- App ---------------------------------------------------------------------

app = FastAPI(title="TOEFL Essay Evaluator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def word_count(text: str) -> int:
    return len(text.split())


def _build_system_prompt() -> str:
    return """You are a TOEFL Independent Writing rater. Output ONLY one valid JSON object with no other text, no markdown, no code fence.

Required keys (exact names):
- "estimated_score": number 0-30
- "subscores": object with "task_response", "coherence_cohesion", "lexical_resource", "grammar" (each number 0-5)
- "strengths": array of strings
- "weaknesses": array of strings
- "top_fixes": array of exactly 3 strings (most important fixes)
- "rewrite_first_paragraph": string (revised first paragraph of the essay)

Output only the raw JSON object, nothing else."""


def _build_user_prompt(prompt: str, essay: str) -> str:
    return f"""Essay topic (prompt):\n{prompt}\n\nEssay to evaluate:\n{essay}"""


def _parse_llm_json(content: str) -> dict[str, Any] | None:
    content = content.strip()
    # Remove optional markdown code block if present
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```\s*$", "", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return None


def _validate_and_shape(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Extract and validate required fields; return None if invalid."""
    try:
        subscores = raw.get("subscores")
        if not isinstance(subscores, dict):
            return None
        sub = {
            "task_response": float(subscores.get("task_response", 0)),
            "coherence_cohesion": float(subscores.get("coherence_cohesion", 0)),
            "lexical_resource": float(subscores.get("lexical_resource", 0)),
            "grammar": float(subscores.get("grammar", 0)),
        }
        for k, v in sub.items():
            if not (0 <= v <= 5):
                return None

        score = float(raw.get("estimated_score", 0))
        if not (0 <= score <= 30):
            return None

        strengths = raw.get("strengths")
        weaknesses = raw.get("weaknesses")
        top_fixes = raw.get("top_fixes")
        rewrite = raw.get("rewrite_first_paragraph")
        if not isinstance(strengths, list) or not all(isinstance(s, str) for s in strengths):
            return None
        if not isinstance(weaknesses, list) or not all(isinstance(w, str) for w in weaknesses):
            return None
        if not isinstance(top_fixes, list) or len(top_fixes) != 3 or not all(isinstance(t, str) for t in top_fixes):
            return None
        if not isinstance(rewrite, str):
            return None

        return {
            "estimated_score": score,
            "subscores": sub,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "top_fixes": top_fixes,
            "rewrite_first_paragraph": rewrite,
        }
    except (TypeError, ValueError):
        return None


def _call_groq(prompt: str, essay: str, fix_json: bool = False) -> str:
    system = _build_system_prompt()
    if fix_json:
        system += "\n\nThe previous response was invalid JSON. Output only the corrected JSON object, nothing else."
    user = _build_user_prompt(prompt, essay)
    resp = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=1024,
    )
    choice = resp.choices[0] if resp.choices else None
    if not choice or not getattr(choice, "message", None):
        raise ValueError("Empty or invalid Groq response")
    return choice.message.content or ""


@app.post("/api/evaluate", response_model=EvaluateResponse)
def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    essay_text = request.essay.strip()
    words = word_count(essay_text)
    if words < MIN_WORDS:
        raise HTTPException(
            status_code=422,
            detail=f"Essay must be at least {MIN_WORDS} words. Current word count: {words}.",
        )

    start = time.perf_counter_ns()
    content: str | None = None
    parsed: dict[str, Any] | None = None
    shaped: dict[str, Any] | None = None

    for attempt, is_retry in enumerate([False, True], start=1):
        try:
            content = _call_groq(request.prompt, essay_text, fix_json=is_retry)
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Evaluation service error: {str(e)}",
            ) from e

        parsed = _parse_llm_json(content)
        if parsed is not None:
            shaped = _validate_and_shape(parsed)
        if shaped is not None:
            break

    if shaped is None:
        raise HTTPException(
            status_code=502,
            detail="Evaluation service returned invalid or incomplete JSON. Please try again.",
        )

    latency_ms = (time.perf_counter_ns() - start) // 1_000_000

    return EvaluateResponse(
        model=GROQ_MODEL,
        estimated_score=shaped["estimated_score"],
        subscores=Subscores(**shaped["subscores"]),
        strengths=shaped["strengths"],
        weaknesses=shaped["weaknesses"],
        top_fixes=shaped["top_fixes"],
        rewrite_first_paragraph=shaped["rewrite_first_paragraph"],
        word_count=words,
        latency_ms=latency_ms,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
