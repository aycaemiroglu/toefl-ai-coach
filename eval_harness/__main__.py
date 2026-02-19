"""
CLI entry point for the offline evaluation harness.

Usage:
    python -m eval_harness --input data/essays --out results
    python -m eval_harness --input data/essays --out results --seed 42
"""
import argparse
import logging
import os
import random
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from eval_harness.runner import discover_essays, evaluate_batch  # noqa: E402
from eval_harness.report import generate_summary  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Run the TOEFL evaluator on a folder of essays and produce a metrics report.",
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Directory containing .txt and/or .json essay files.",
    )
    parser.add_argument(
        "--out", "-o",
        default="results",
        help="Output directory for results.jsonl and summary.md (default: results).",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        default=None,
        help="Random seed for deterministic runs.",
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=0.0,
        help="Seconds to wait between LLM calls (avoids rate-limits). Default: 0.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.seed is not None:
        random.seed(args.seed)
        os.environ["EVAL_HARNESS_SEED"] = str(args.seed)
        logging.info("Random seed set to %d", args.seed)

    input_dir = Path(args.input)
    out_dir = Path(args.out)

    if not input_dir.is_dir():
        logging.error("Input directory does not exist: %s", input_dir)
        sys.exit(1)

    essays = discover_essays(input_dir)
    logging.info("Found %d essay(s) in %s", len(essays), input_dir)

    jsonl_path = out_dir / "results.jsonl"
    results = evaluate_batch(essays, jsonl_path, delay=args.delay)
    logging.info("Results written to %s", jsonl_path)

    summary_path = out_dir / "summary.md"
    generate_summary(results, summary_path)
    logging.info("Summary written to %s", summary_path)

    ok_count = sum(1 for r in results if "_error" not in r)
    err_count = len(results) - ok_count
    logging.info("Done: %d succeeded, %d errored.", ok_count, err_count)


if __name__ == "__main__":
    main()
