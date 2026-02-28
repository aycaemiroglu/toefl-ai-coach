"""
Core runner: reads essays from a folder, evaluates each through the same
pipeline used by the FastAPI endpoint, writes results to JSONL.
"""
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

_backend = Path(__file__).resolve().parent.parent / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from main import evaluate_essay_core  # noqa: E402

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = (
    "Do you agree or disagree with the following statement? "
    "Technology has made our lives easier. "
    "Use specific reasons and examples to support your answer."
)


def _load_essay_file(path: Path) -> dict[str, Any]:
    """
    Load a single essay file.
    .json  -> expects {"essay": "...", "prompt_id": "...", "level": "...", "prompt": "..."}
    .txt   -> entire file contents treated as the essay text
    """
    if path.suffix == ".json":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if "essay" not in data:
            raise ValueError(f"{path.name}: JSON must contain an 'essay' field")
        return {
            "essay": data["essay"],
            "prompt": data.get("prompt", DEFAULT_PROMPT),
            "prompt_id": data.get("prompt_id"),
            "level": data.get("level"),
            "source_file": path.name,
        }

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{path.name}: file is empty")
    return {
        "essay": text,
        "prompt": DEFAULT_PROMPT,
        "prompt_id": None,
        "level": None,
        "source_file": path.name,
    }


def discover_essays(input_dir: Path) -> list[dict[str, Any]]:
    """Find all .txt and .json essay files in the input directory."""
    files = sorted(
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix in (".txt", ".json")
    )
    if not files:
        raise FileNotFoundError(f"No .txt or .json files found in {input_dir}")
    essays = []
    for f in files:
        try:
            essays.append(_load_essay_file(f))
        except Exception as e:
            logger.warning("Skipping %s: %s", f.name, e)
    return essays


def evaluate_batch(
    essays: list[dict[str, Any]],
    output_path: Path,
    delay: float = 0.0,
) -> list[dict[str, Any]]:
    """
    Evaluate each essay through evaluate_essay_core and write results to JSONL.
    Returns the list of result dicts (for the report generator).
    """
    results: list[dict[str, Any]] = []
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as out:
        for i, entry in enumerate(essays, 1):
            source = entry["source_file"]
            logger.info("[%d/%d] Evaluating %s …", i, len(essays), source)
            try:
                resp = evaluate_essay_core(
                    prompt=entry["prompt"],
                    essay=entry["essay"],
                    prompt_id=entry.get("prompt_id"),
                )
                result = resp.model_dump()
                result["essay_text"] = entry["essay"]
                result["_meta"] = {
                    "source_file": source,
                    "level": entry.get("level"),
                }
                results.append(result)
                out.write(json.dumps(result, ensure_ascii=False) + "\n")
                logger.info(
                    "  -> score=%s  tier=%s  confidence=%s",
                    result["scoring"]["final"],
                    result["length"]["tier"],
                    result["confidence"]["level"],
                )
            except Exception as e:
                logger.error("  -> FAILED: %s", e)
                error_record = {
                    "_meta": {"source_file": source, "level": entry.get("level")},
                    "_error": str(e),
                }
                results.append(error_record)
                out.write(json.dumps(error_record, ensure_ascii=False) + "\n")

            if delay > 0 and i < len(essays):
                time.sleep(delay)

    return results
