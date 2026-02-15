"""
Minimal FastAPI backend for TOEFL essay evaluation via Groq (OpenAI-compatible API).

Example detailed response (POST /api/evaluate?detailed=true):
{
  "model": "llama-3.1-8b-instant",
  "estimated_score": 24.0,
  "subscores": {
    "task_response": 4.5,
    "coherence_cohesion": 4.0,
    "lexical_resource": 4.0,
    "grammar": 3.5
  },
  "strengths": [
    {
      "label": "Clear position",
      "explanation": "The thesis is stated in the first paragraph.",
      "evidence": "I believe that technology has made our lives easier."
    },
    {
      "label": "Relevant examples",
      "explanation": "Concrete support is given for the main idea.",
      "evidence": null
    }
  ],
  "weaknesses": [
    {
      "label": "Repetition",
      "explanation": "The word 'clearly' is overused.",
      "evidence": "Clearly, this shows that clearly we need"
    }
  ],
  "top_fixes": ["Vary transition words", "Add one counter-argument", "Shorten run-on in paragraph 2"],
  "rewrite_first_paragraph": "Technology has changed how we work and communicate. I believe...",
  "word_count": 287,
  "latency_ms": 1520
}
"""
import json
import os
import re
import time
from typing import Any

from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
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


# --- Legacy (flat lists) ---
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


# --- Detailed (label + explanation + evidence) ---
class StrengthItem(BaseModel):
    label: str
    explanation: str
    evidence: str | None = None


class WeaknessItem(BaseModel):
    label: str
    explanation: str
    evidence: str | None = None
    evidence_reason: str | None = None  # when evidence is null, e.g. "conceptual issue, not tied to a single sentence"


class EvaluateResponseDetailed(BaseModel):
    model: str
    estimated_score: float = Field(..., ge=0, le=30)
    subscores: Subscores
    strengths: list[StrengthItem]
    weaknesses: list[WeaknessItem]
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


def _build_system_prompt(detailed: bool = False) -> str:
    if not detailed:
        return """You are a TOEFL Independent Writing rater. Output ONLY one valid JSON object with no other text, no markdown, no code fence.

Required keys (exact names):
- "estimated_score": number 0-30
- "subscores": object with "task_response", "coherence_cohesion", "lexical_resource", "grammar" (each number 0-5)
- "strengths": array of strings
- "weaknesses": array of strings
- "top_fixes": array of exactly 3 strings (most important fixes)
- "rewrite_first_paragraph": string (revised first paragraph of the essay)

Output only the raw JSON object, nothing else."""

    return """You are a TOEFL Independent Writing rater. Output ONLY one valid JSON object with no other text, no markdown, no code fence.

Required keys (exact names):
- "estimated_score": number 0-30
- "subscores": object with "task_response", "coherence_cohesion", "lexical_resource", "grammar" (each number 0-5)
- "strengths": array of objects. Each object MUST have exactly three keys: "label" (string, short title), "explanation" (string, brief reason), "evidence" (string or null). For "evidence": copy an exact phrase from the student's essay that shows this strength (max 20 words), or use null if no clear quote fits.
- "weaknesses": array of objects. Each MUST have "label", "explanation", "evidence" (exact quote from essay, max 20 words, or null). When evidence is null, include "evidence_reason" (short string explaining why, e.g. "conceptual issue, not tied to a single sentence" or "repeated across paragraphs").
- "top_fixes": array of exactly 3 strings (most important fixes)
- "rewrite_first_paragraph": string (revised first paragraph of the essay)

Important: "evidence" must be a verbatim substring of the essay. When you cannot quote exactly, set evidence to null and set "evidence_reason". Output only the raw JSON object, nothing else."""


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


def _ensure_evidence_substring(evidence: str | None, essay: str, max_words: int = 20) -> str | None:
    """If evidence is not an exact substring of essay (or too long), return None."""
    if not evidence or not isinstance(evidence, str):
        return None
    evidence = evidence.strip()
    if not evidence:
        return None
    if len(evidence.split()) > max_words:
        return None
    return evidence if evidence in essay else None


def _validate_and_shape_detailed(raw: dict[str, Any], essay: str) -> dict[str, Any] | None:
    """Validate and shape for detailed response; enforce evidence as substring or null."""
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

        top_fixes = raw.get("top_fixes")
        rewrite = raw.get("rewrite_first_paragraph")
        if not isinstance(top_fixes, list) or len(top_fixes) != 3 or not all(isinstance(t, str) for t in top_fixes):
            return None
        if not isinstance(rewrite, str):
            return None

        def parse_strength_item(item: Any, essay_text: str) -> dict[str, str | None] | None:
            if not isinstance(item, dict):
                return None
            label = item.get("label")
            explanation = item.get("explanation")
            evidence = item.get("evidence")
            if not isinstance(label, str) or not isinstance(explanation, str):
                return None
            evidence_clean = _ensure_evidence_substring(
                evidence if isinstance(evidence, str) else None, essay_text
            )
            return {"label": label, "explanation": explanation, "evidence": evidence_clean}

        def parse_weakness_item(item: Any, essay_text: str) -> dict[str, str | None] | None:
            if not isinstance(item, dict):
                return None
            label = item.get("label")
            explanation = item.get("explanation")
            evidence = item.get("evidence")
            evidence_reason = item.get("evidence_reason")
            if not isinstance(label, str) or not isinstance(explanation, str):
                return None
            evidence_clean = _ensure_evidence_substring(
                evidence if isinstance(evidence, str) else None, essay_text
            )
            reason = evidence_reason if isinstance(evidence_reason, str) and evidence_reason.strip() else None
            if evidence_clean is None and reason is None:
                reason = "Not an exact quote from the essay"
            return {"label": label, "explanation": explanation, "evidence": evidence_clean, "evidence_reason": reason}

        strengths_raw = raw.get("strengths")
        weaknesses_raw = raw.get("weaknesses")
        if not isinstance(strengths_raw, list) or not isinstance(weaknesses_raw, list):
            return None
        strengths = [parse_strength_item(s, essay) for s in strengths_raw]
        weaknesses = [parse_weakness_item(w, essay) for w in weaknesses_raw]
        if None in strengths or None in weaknesses:
            return None
        strengths = [s for s in strengths if s is not None]
        weaknesses = [w for w in weaknesses if w is not None]

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


def _call_groq(prompt: str, essay: str, fix_json: bool = False, detailed: bool = False) -> str:
    system = _build_system_prompt(detailed=detailed)
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


@app.post(
    "/api/evaluate",
    summary="Evaluate TOEFL essay",
    response_description="Structured evaluation; use ?detailed=true for strengths/weaknesses with label, explanation, and evidence quote.",
)
def evaluate(
    request: EvaluateRequest,
    detailed: bool = Query(
        False,
        description="If true, return strengths/weaknesses as objects with label, explanation, and evidence (exact quote from essay or null).",
    ),
) -> EvaluateResponse | EvaluateResponseDetailed:
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
            content = _call_groq(
                request.prompt, essay_text, fix_json=is_retry, detailed=detailed
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"Evaluation service error: {str(e)}",
            ) from e

        parsed = _parse_llm_json(content)
        if parsed is not None:
            shaped = (
                _validate_and_shape_detailed(parsed, essay_text)
                if detailed
                else _validate_and_shape(parsed)
            )
        if shaped is not None:
            break

    if shaped is None:
        raise HTTPException(
            status_code=502,
            detail="Evaluation service returned invalid or incomplete JSON. Please try again.",
        )

    latency_ms = (time.perf_counter_ns() - start) // 1_000_000
    subscores_obj = Subscores(**shaped["subscores"])

    if detailed:
        out = EvaluateResponseDetailed(
            model=GROQ_MODEL,
            estimated_score=shaped["estimated_score"],
            subscores=subscores_obj,
            strengths=[StrengthItem(**s) for s in shaped["strengths"]],
            weaknesses=[WeaknessItem(**w) for w in shaped["weaknesses"]],
            top_fixes=shaped["top_fixes"],
            rewrite_first_paragraph=shaped["rewrite_first_paragraph"],
            word_count=words,
            latency_ms=latency_ms,
        )
        return out
    return EvaluateResponse(
        model=GROQ_MODEL,
        estimated_score=shaped["estimated_score"],
        subscores=subscores_obj,
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
