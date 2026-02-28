"""
Simple file-based cache for LLM responses.

Cache key = SHA-256(essay_text + model_name + prompt_version).
Stores the raw LLM response string so downstream deterministic logic
always runs fresh — only the stochastic LLM call is cached.
"""
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "llm_responses"


def _cache_key(essay_text: str, model_name: str, prompt_version: str) -> str:
    blob = f"{essay_text.strip()}\x00{model_name}\x00{prompt_version}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def get(essay_text: str, model_name: str, prompt_version: str) -> str | None:
    """Return cached LLM response string, or None on miss."""
    key = _cache_key(essay_text, model_name, prompt_version)
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text("utf-8"))
        logger.debug("Cache HIT: %s", key[:12])
        return data.get("response")
    except (json.JSONDecodeError, OSError):
        return None


def put(
    essay_text: str,
    model_name: str,
    prompt_version: str,
    response: str,
    extra: dict[str, Any] | None = None,
) -> None:
    """Store an LLM response string in the file cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _cache_key(essay_text, model_name, prompt_version)
    path = CACHE_DIR / f"{key}.json"
    data: dict[str, Any] = {
        "response": response,
        "model_name": model_name,
        "prompt_version": prompt_version,
        "essay_sha256": hashlib.sha256(essay_text.strip().encode()).hexdigest()[:16],
    }
    if extra:
        data.update(extra)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    logger.debug("Cache STORE: %s", key[:12])


def clear() -> int:
    """Remove all cached responses. Returns count of files removed."""
    if not CACHE_DIR.exists():
        return 0
    count = 0
    for p in CACHE_DIR.glob("*.json"):
        p.unlink()
        count += 1
    return count
