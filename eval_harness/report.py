"""
Generate a Markdown summary report from evaluation results.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


def _safe(results: list[dict], key_path: str) -> list[Any]:
    """Extract nested values, skipping errored entries."""
    parts = key_path.split(".")
    vals = []
    for r in results:
        if "_error" in r:
            continue
        obj: Any = r
        for p in parts:
            if isinstance(obj, dict):
                obj = obj.get(p)
            else:
                obj = None
                break
        if obj is not None:
            vals.append(obj)
    return vals


def _avg(values: list[float | int]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def _pct(num: int, den: int) -> str:
    return f"{num / den * 100:.1f}%" if den else "N/A"


def generate_summary(results: list[dict[str, Any]], output_path: Path) -> str:
    ok = [r for r in results if "_error" not in r]
    errored = [r for r in results if "_error" in r]

    tiers = Counter(_safe(ok, "length_evaluation.tier"))
    confidence_levels = Counter(_safe(ok, "confidence.level"))

    raw_scores = _safe(ok, "scoring.raw_score_30")
    cal_scores = _safe(ok, "scoring.calibrated_score_30")
    factors = _safe(ok, "scoring.length_factor")
    conf_numerics = _safe(ok, "confidence.numeric_score_0_100")

    deltas = [r - c for r, c in zip(raw_scores, cal_scores)]

    # Confidence average by tier
    conf_by_tier: dict[str, list[int]] = {}
    for r in ok:
        tier = r.get("length_evaluation", {}).get("tier", "unknown")
        ns = r.get("confidence", {}).get("numeric_score_0_100")
        if ns is not None:
            conf_by_tier.setdefault(tier, []).append(ns)

    # Evidence stats
    total_weaknesses = 0
    with_evidence = 0
    with_null = 0
    weakness_labels: list[str] = []
    for r in ok:
        for w in r.get("evidence", {}).get("weaknesses", []):
            total_weaknesses += 1
            weakness_labels.append(w.get("label", "unknown"))
            if w.get("evidence") is not None:
                with_evidence += 1
            else:
                with_null += 1

    top_labels = Counter(weakness_labels).most_common(10)

    # Calibration impact buckets
    buckets = {"no change (0)": 0, "small (0-2)": 0, "medium (2-5)": 0, "large (>5)": 0}
    for d in deltas:
        if d == 0:
            buckets["no change (0)"] += 1
        elif d <= 2:
            buckets["small (0-2)"] += 1
        elif d <= 5:
            buckets["medium (2-5)"] += 1
        else:
            buckets["large (>5)"] += 1

    lines = [
        "# Evaluation Summary",
        "",
        f"**Total essays:** {len(results)} ({len(ok)} succeeded, {len(errored)} errored)",
        "",
        "## Length Tier Distribution",
        "",
        "| Tier | Count | % |",
        "|------|------:|--:|",
    ]
    for tier in ("short", "recommended", "ideal"):
        c = tiers.get(tier, 0)
        lines.append(f"| {tier} | {c} | {_pct(c, len(ok))} |")

    lines += [
        "",
        "## Scoring",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| Avg raw score | {_avg(raw_scores)} |",
        f"| Avg calibrated score | {_avg(cal_scores)} |",
        f"| Avg length factor | {_avg(factors)} |",
        f"| Avg calibration delta (raw - cal) | {_avg(deltas)} |",
        "",
        "## Calibration Impact Distribution",
        "",
        "| Bucket | Count | % |",
        "|--------|------:|--:|",
    ]
    for label, cnt in buckets.items():
        lines.append(f"| {label} | {cnt} | {_pct(cnt, len(ok))} |")

    lines += [
        "",
        "## Confidence",
        "",
        "| Level | Count | % |",
        "|-------|------:|--:|",
    ]
    for lv in ("High", "Medium", "Low"):
        c = confidence_levels.get(lv, 0)
        lines.append(f"| {lv} | {c} | {_pct(c, len(ok))} |")

    lines += [
        "",
        f"**Average confidence score:** {_avg(conf_numerics)}",
        "",
        "### Average Confidence by Length Tier",
        "",
        "| Tier | Avg Confidence Score |",
        "|------|---------------------:|",
    ]
    for tier in ("short", "recommended", "ideal"):
        vals = conf_by_tier.get(tier, [])
        lines.append(f"| {tier} | {_avg(vals)} |")

    lines += [
        "",
        "## Evidence Quality",
        "",
        f"| Metric | Value |",
        f"|--------|------:|",
        f"| Total weaknesses | {total_weaknesses} |",
        f"| With evidence (substring) | {with_evidence} ({_pct(with_evidence, total_weaknesses)}) |",
        f"| With null evidence (+ reason) | {with_null} ({_pct(with_null, total_weaknesses)}) |",
        "",
        "## Top 10 Most Common Weakness Labels",
        "",
        "| # | Label | Count |",
        "|--:|-------|------:|",
    ]
    for rank, (label, cnt) in enumerate(top_labels, 1):
        lines.append(f"| {rank} | {label} | {cnt} |")

    if errored:
        lines += [
            "",
            "## Errors",
            "",
            "| File | Error |",
            "|------|-------|",
        ]
        for r in errored:
            f = r.get("_meta", {}).get("source_file", "?")
            e = r.get("_error", "unknown")
            lines.append(f"| {f} | {e} |")

    md = "\n".join(lines) + "\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md, encoding="utf-8")
    return md
