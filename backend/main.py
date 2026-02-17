"""
Minimal FastAPI backend for TOEFL essay evaluation via Groq (OpenAI-compatible API).

Example detailed response (POST /api/evaluate?detailed=true):
{
  "model": "llama-3.1-8b-instant",
  "estimated_score": 22.4,
  "subscores": {
    "task_response": 4.5,
    "coherence_cohesion": 4.0,
    "lexical_resource": 4.0,
    "grammar": 3.5
  },
  "calibration": {
    "recommended_words": 220,
    "word_count": 205,
    "length_factor": 0.9318,
    "raw_score": 24.0,
    "calibrated_score": 22.4,
    "note": "Shorter than recommended length; score reduced."
  },
  "confidence": {
    "level": "Medium",
    "numeric_score": 60,
    "reasons": [
      "Essay is below optimal length; reliability is reduced.",
      "Length-based calibration reduced the score; reliability is lower."
    ],
    "signals": {
      "word_count": 205,
      "subscore_variance": 1.0,
      "weakness_count": 1,
      "has_counterargument_weakness": true,
      "raw_score": 60.0,
      "final_score": 24.0
    }
  },
  "strengths": [
    {
      "label": "Clear position",
      "explanation": "The thesis is stated in the first paragraph.",
      "evidence": "I believe that technology has made our lives easier."
    }
  ],
  "weaknesses": [
    {
      "label": "Overuse of simple vocabulary",
      "explanation": "Words like 'very' and 'important' are repeated.",
      "evidence": "Technology is very important and very useful in our daily lives.",
      "evidence_reason": null
    }
  ],
  "top_fixes": ["Vary transition words", "Add one counter-argument", "Shorten run-on in paragraph 2"],
  "rewrite_first_paragraph": "Technology has changed how we work and communicate. I believe...",
  "word_count": 205,
  "latency_ms": 1520
}
"""
import json
import logging
import os
import re
import time
from typing import Any, Literal

from pathlib import Path

logger = logging.getLogger(__name__)

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
MIN_WORDS = 120
RECOMMENDED_WORDS = 220
FULL_CONFIDENCE_WORDS = 250

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


ConfidenceLevel = Literal["Low", "Medium", "High"]


class ConfidenceSignals(BaseModel):
    word_count: int
    subscore_variance: float
    weakness_count: int
    has_counterargument_weakness: bool
    raw_score: float
    final_score: float


class Confidence(BaseModel):
    level: ConfidenceLevel
    numeric_score: int = Field(..., ge=0, le=100)
    reasons: list[str]
    signals: ConfidenceSignals


class Calibration(BaseModel):
    recommended_words: int
    word_count: int
    length_factor: float = Field(..., ge=0, le=1)
    raw_score: float = Field(..., ge=0, le=30)
    calibrated_score: float = Field(..., ge=0, le=30)
    note: str


# --- Legacy (flat lists) ---
class EvaluateResponse(BaseModel):
    model: str
    estimated_score: float = Field(..., ge=0, le=30)
    subscores: Subscores
    calibration: Calibration
    confidence: Confidence
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
    calibration: Calibration
    confidence: Confidence
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


# --- Length-based score calibration (server-side only) ---
def _compute_calibration(wc: int, raw_score: float) -> Calibration:
    """
    Apply smooth length penalty to the final score.
    length_factor = min(1.0, word_count / RECOMMENDED_WORDS)
    Subscores are NOT modified.
    """
    length_factor = min(1.0, wc / RECOMMENDED_WORDS)
    calibrated = round(raw_score * length_factor, 1)
    calibrated = max(0.0, min(30.0, calibrated))

    if length_factor >= 1.0:
        note = "Essay meets recommended length; no score adjustment."
    elif wc < 180:
        note = "Significantly shorter than recommended length; score substantially reduced."
    else:
        note = "Shorter than recommended length; score reduced."

    return Calibration(
        recommended_words=RECOMMENDED_WORDS,
        word_count=wc,
        length_factor=round(length_factor, 4),
        raw_score=raw_score,
        calibrated_score=calibrated,
        note=note,
    )


# --- Confidence computation (server-side only) ---
def _compute_confidence(
    word_count: int,
    subscores: Subscores,
    final_score: float,
    weaknesses: list[dict[str, Any]],
    calibration_delta: float = 0.0,
) -> Confidence:
    """
    Compute confidence score (0-100) and level using multi-factor heuristics.
    LLM must NOT generate confidence; this is strictly server-side.
    calibration_delta = raw_score - calibrated_score (how much calibration reduced).
    """
    score = 100.0
    reasons: list[str] = []
    
    # Signals for debugging
    subscore_values = [
        subscores.task_response,
        subscores.coherence_cohesion,
        subscores.lexical_resource,
        subscores.grammar,
    ]
    subscore_variance = max(subscore_values) - min(subscore_values)
    weakness_count = len(weaknesses)
    has_counterargument_weakness = any(
        "counterargument" in (w.get("label") or "").lower() or "counter-argument" in (w.get("label") or "").lower()
        for w in weaknesses
    )
    
    # Word count penalty
    if word_count < 180:
        score -= 35
        reasons.append("Essay is shorter than recommended length; scoring is less stable.")
    elif word_count < 220:
        score -= 20
        reasons.append("Essay is below optimal length; reliability is reduced.")
    elif word_count < 250:
        score -= 10
        reasons.append("Essay length is slightly below ideal range.")
    
    # Subscore variance penalty
    if subscore_variance >= 3:
        score -= 20
        reasons.append("Subscores vary widely, indicating uncertainty.")
    elif subscore_variance == 2:
        score -= 10
        reasons.append("Subscores show moderate variance.")
    
    # High-score short-essay penalty
    if word_count < 220 and final_score >= 25:
        score -= 20
        reasons.append("High overall score with short essay suggests possible model generosity.")
    if word_count < 180 and final_score >= 23:
        score -= 15
        reasons.append("High score for very short essay may be optimistic.")
    
    # Weakness-score mismatch penalty
    if weakness_count >= 3 and final_score >= 25:
        score -= 15
        reasons.append("Multiple weaknesses detected; overall score may be optimistic.")
    if has_counterargument_weakness and subscores.task_response >= 4:
        score -= 10
        reasons.append("Missing counterargument should reduce task reliability.")
    
    # Calibration-aware penalty
    if word_count < 220 and calibration_delta >= 2:
        score -= 10
        reasons.append("Length-based calibration reduced the score; reliability is lower.")
    
    raw_score = score  # Before clamping
    # Clamp to [0, 100]
    score = max(0, min(100, int(round(score))))
    
    # Map to level
    if score >= 80:
        level: ConfidenceLevel = "High"
    elif score >= 50:
        level = "Medium"
    else:
        level = "Low"
    
    # If no reasons (shouldn't happen), add a default
    if not reasons:
        reasons.append("Confidence computed from essay characteristics.")
    
    signals = ConfidenceSignals(
        word_count=word_count,
        subscore_variance=subscore_variance,
        weakness_count=weakness_count,
        has_counterargument_weakness=has_counterargument_weakness,
        raw_score=raw_score,
        final_score=final_score,
    )
    
    # Debug logging (if DEBUG env var set)
    if os.getenv("DEBUG_CONFIDENCE", "").lower() in ("1", "true", "yes"):
        logger.info(
            "Confidence computed: level=%s, score=%d, reasons=%s, signals=%s",
            level,
            score,
            reasons,
            signals.model_dump(),
        )
    
    return Confidence(
        level=level,
        numeric_score=score,
        reasons=reasons,
        signals=signals,
    )


# --- Quote normalization (smart quotes → ASCII) for substring checks ---
def _normalize_quotes(s: str) -> str:
    if not s:
        return s
    return (
        s.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )


# --- Lexical evidence extraction (server-side) ---
_STOPWORDS = frozenset(
    "the a an is are was were be been being have has had do does did will would could "
    "should may might must can to of in for on with at by from as it its that this "
    "and or but if then else when so i you we they he she it".split()
)


def _tokenize_words(text: str) -> list[str]:
    """Lowercased words, split on non-letters."""
    return re.findall(r"[a-z]+", text.lower())


def _get_repeated_content_words(essay: str, min_count: int = 2, top_n: int = 10) -> list[tuple[str, int]]:
    """Top repeated content words (exclude stopwords), sorted by count descending."""
    words = _tokenize_words(essay)
    counts: dict[str, int] = {}
    for w in words:
        if w not in _STOPWORDS and len(w) > 1:
            counts[w] = counts.get(w, 0) + 1
    repeated = [(w, c) for w, c in counts.items() if c >= min_count]
    repeated.sort(key=lambda x: -x[1])
    return repeated[:top_n]


def _get_sentences(essay: str) -> list[str]:
    """Split into sentences (exact substrings of essay)."""
    parts = re.split(r"(?<=[.!?])\s+", essay)
    return [p.strip() for p in parts if p.strip()]


def _get_lexical_evidence(essay: str, max_words: int = 25) -> tuple[str | None, list[str]]:
    """
    Find one sentence that best demonstrates repeated/simple vocabulary.
    Returns (sentence_or_none, list_of_repeated_words_that_triggered).
    Sentence is exact substring of essay, <= max_words.
    """
    repeated = _get_repeated_content_words(essay)
    if not repeated:
        return None, []
    trigger_words = [w for w, _ in repeated]
    sentences = _get_sentences(essay)
    best: str | None = None
    best_count = 0
    for sent in sentences:
        if len(sent.split()) > max_words:
            continue
        words_in_sent = set(_tokenize_words(sent)) - _STOPWORDS
        overlap = sum(1 for w, _ in repeated if w in words_in_sent)
        if overlap > best_count:
            best_count = overlap
            best = sent
    if best and best_count > 0:
        return best, trigger_words[:5]
    return None, []


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

Do not output confidence; it will be computed server-side.

Output only the raw JSON object, nothing else."""

    return """You are a TOEFL Independent Writing rater. Output ONLY one valid JSON object with no other text, no markdown, no code fence.

Required keys (exact names):
- "estimated_score": number 0-30
- "subscores": object with "task_response", "coherence_cohesion", "lexical_resource", "grammar" (each number 0-5)
- "strengths": array of objects. Each object MUST have exactly three keys: "label" (string, short title), "explanation" (string, brief reason), "evidence" (string or null). For "evidence": copy an exact phrase from the student's essay that shows this strength (max 20 words), or use null if no clear quote fits.
- "weaknesses": array of objects. Each MUST have "label", "explanation", "evidence", and optionally "evidence_reason". For "evidence": select ONE full sentence from the essay that is the MOST representative of the weakness. Choose the strongest and most obvious sentence demonstrating the issue. Prefer sentences that clearly show repetition, shallow reasoning, or structural weakness; avoid neutral or generic sentences. If multiple sentences qualify, choose the one with the strongest linguistic signal. The sentence must be an exact verbatim substring (copy character-for-character), max 25 words. If the weakness relates to repetition, simple vocabulary, or sentence structure, you MUST select the exact sentence that shows this. If no single sentence clearly demonstrates the issue (e.g. conceptual or organizational), set "evidence" to null and set "evidence_reason" to exactly: "Conceptual issue not tied to a single sentence."
- "top_fixes": array of exactly 3 strings (most important fixes)
- "rewrite_first_paragraph": string (revised first paragraph of the essay)

Important: weakness "evidence" must be one full sentence, verbatim from the essay, max 25 words. Choose the strongest and most obvious sentence demonstrating the issue. For repetition, word choice, or grammar/structure weaknesses, always provide the exact sentence. Only use evidence=null when the issue cannot be shown by one sentence.

Do not output confidence; it will be computed server-side.

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


def _ensure_evidence_substring(
    evidence: str | None, essay: str, max_words: int = 20, log_reject: bool = False
) -> str | None:
    """If evidence is not an exact substring of essay (or too long), return None. Normalizes smart quotes for check."""
    if not evidence or not isinstance(evidence, str):
        return None
    evidence = evidence.strip()
    if not evidence:
        return None
    if len(evidence.split()) > max_words:
        if log_reject:
            logger.info("Evidence rejected (over %d words): %r", max_words, evidence[:100])
        return None
    norm_essay = _normalize_quotes(essay)
    norm_evidence = _normalize_quotes(evidence)
    if norm_evidence not in norm_essay:
        if log_reject:
            logger.info("Evidence rejected (not exact substring): %r", evidence[:100])
        return None
    # Return slice from original essay so response is exact substring
    start = norm_essay.find(norm_evidence)
    end = start + len(norm_evidence)
    return essay[start:end]


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
                evidence if isinstance(evidence, str) else None,
                essay_text,
                max_words=25,
                log_reject=True,
            )
            reason = evidence_reason if isinstance(evidence_reason, str) and evidence_reason.strip() else None
            if evidence_clean is None and reason is None:
                reason = "Conceptual issue not tied to a single sentence."
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

        # Server-side evidence for lexical weakness when LLM returned null
        _LEXICAL_LABEL_KEYWORDS = ("simple vocabulary", "repetition", "limited lexical", "lexical variety", "word choice", "overuse")
        lexical_evidence, trigger_words = _get_lexical_evidence(essay, max_words=25)
        for w in weaknesses:
            if w.get("evidence") is not None:
                continue
            label_lower = (w.get("label") or "").lower()
            if not any(kw in label_lower for kw in _LEXICAL_LABEL_KEYWORDS):
                continue
            if lexical_evidence and len(lexical_evidence.split()) <= 25:
                # Ensure it's substring (already is from _get_sentences)
                if lexical_evidence.strip() in essay or _normalize_quotes(lexical_evidence.strip()) in _normalize_quotes(essay):
                    w["evidence"] = lexical_evidence.strip()
                    w["evidence_reason"] = None
                    logger.info(
                        "evidence_overridden=true | lexical weakness: label=%r, trigger_words=%s, evidence=%r",
                        w.get("label"),
                        trigger_words,
                        lexical_evidence[:60],
                    )

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
    raw_score = shaped["estimated_score"]

    # Length-based calibration (subscores untouched)
    calibration = _compute_calibration(words, raw_score)
    calibrated_score = calibration.calibrated_score
    calibration_delta = raw_score - calibrated_score

    # Normalize weaknesses for confidence computation
    if detailed:
        weaknesses_for_confidence = shaped["weaknesses"]  # Already list of dicts
    else:
        weaknesses_for_confidence = [{"label": w} for w in shaped["weaknesses"]]

    confidence = _compute_confidence(
        words, subscores_obj, raw_score, weaknesses_for_confidence,
        calibration_delta=calibration_delta,
    )

    if detailed:
        out = EvaluateResponseDetailed(
            model=GROQ_MODEL,
            estimated_score=calibrated_score,
            subscores=subscores_obj,
            calibration=calibration,
            confidence=confidence,
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
        estimated_score=calibrated_score,
        subscores=subscores_obj,
        calibration=calibration,
        confidence=confidence,
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
