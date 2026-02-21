"""
Regenerate golden snapshot files from the current API responses.

Usage (from backend/):
    python -m tests.update_golden

Only run this intentionally after a contract change.
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from fastapi.testclient import TestClient
from main import app

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
DYNAMIC_KEYS = {"request_id", "timestamps"}


def _strip_dynamic(data: dict) -> dict:
    return {k: v for k, v in data.items() if k not in DYNAMIC_KEYS}


def main():
    GOLDEN_DIR.mkdir(exist_ok=True)

    with open(FIXTURES_DIR / "essays.json") as f:
        essays = json.load(f)

    client = TestClient(app)

    for key in ("short", "recommended", "ideal"):
        mock_resp = essays["mock_llm_responses"][key]
        with patch("main._call_groq", return_value=json.dumps(mock_resp)):
            r = client.post(
                "/api/evaluate",
                json={
                    "prompt": essays["prompt"],
                    "essay": essays["essays"][key]["text"],
                    "prompt_id": essays["prompt_id"],
                },
            )
        assert r.status_code == 200, f"Failed for {key}: {r.text}"
        clean = _strip_dynamic(r.json())
        out_path = GOLDEN_DIR / f"{key}.json"
        with open(out_path, "w") as f:
            json.dump(clean, f, indent=2, ensure_ascii=False)
        print(f"  wrote {out_path}")

    print("Golden files updated.")


if __name__ == "__main__":
    main()
