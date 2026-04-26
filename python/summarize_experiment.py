#!/usr/bin/env python3
"""Create a compact Markdown report from an experiment series JSON file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from autotune_tu import lookup_objective


DEFAULT_OBJECTIVES = (
    "selected_ir_share_percent",
    "dominant_function_share_percent",
    "top_3_share_percent",
    "top_5_share_percent",
    "size_concentration_hhi",
    "size_gini",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize baseline-vs-best TU metrics from series.json."
    )
    parser.add_argument("series_json", help="Path to experiment series.json.")
    parser.add_argument(
        "--output",
        default="",
        help="Optional path to write Markdown report.",
    )
    parser.add_argument(
        "--objectives",
        default=",".join(DEFAULT_OBJECTIVES),
        help="Comma-separated objective metric names.",
    )
    return parser.parse_args()


def parse_csv(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    if abs(value) >= 100:
        return f"{value:.2f}"
    return f"{value:.4f}"


def metric_value(payload: dict[str, Any] | None, objective: str) -> float | None:
    if payload is None:
        return None
    try:
        return lookup_objective(payload, objective)
    except (KeyError, TypeError, ValueError):
        return None


def action_text(actions: list[int]) -> str:
    return "baseline" if not actions else ",".join(str(action) for action in actions)


def best_for_objective(
    rows: list[dict[str, Any]],
    objective: str,
) -> tuple[dict[str, Any] | None, float | None]:
    best_row = None
    best_value = None
    for row in rows:
        value = metric_value(row.get("payload"), objective)
        if value is None:
            continue
        if best_value is None or value > best_value:
            best_row = row
            best_value = value
    return best_row, best_value


def render_report(series: dict[str, Any], objectives: list[str]) -> str:
    evaluations = [row for row in series.get("evaluations", []) if row.get("payload")]
    benchmarks = series.get("config", {}).get("benchmarks", [])
    lines = [
        "# Experiment Series Summary",
        "",
        f"- Created at UTC: `{series.get('created_at_utc', 'unknown')}`",
        f"- CompilerGym: `{series.get('environment', {}).get('compiler_gym_version', 'unknown')}`",
        f"- Evaluations: {series.get('successful_evaluations', 0)} successful, "
        f"{series.get('failed_evaluations', 0)} failed",
        f"- Trials per benchmark: {series.get('config', {}).get('trials', 'unknown')}",
        f"- Sequence length: {series.get('config', {}).get('steps', 'unknown')}",
        f"- Seed: {series.get('config', {}).get('seed', 'unknown')}",
        "",
    ]

    for benchmark in benchmarks:
        rows = [row for row in evaluations if row["benchmark"] == benchmark]
        if not rows:
            lines.extend([f"## {benchmark}", "", "No successful evaluations.", ""])
            continue

        baseline = next((row for row in rows if row["kind"] == "baseline"), None)
        lines.extend(
            [
                f"## {benchmark}",
                "",
                "| Objective | Baseline | Best | Delta | Trial | Actions |",
                "| --- | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for objective in objectives:
            baseline_value = metric_value(baseline.get("payload"), objective) if baseline else None
            best_row, best_value = best_for_objective(rows, objective)
            delta = (
                None
                if baseline_value is None or best_value is None
                else best_value - baseline_value
            )
            trial = best_row["trial"] if best_row else "n/a"
            actions = action_text(best_row["actions"]) if best_row else "n/a"
            lines.append(
                f"| `{objective}` | {fmt(baseline_value)} | {fmt(best_value)} | "
                f"{fmt(delta)} | {trial} | `{actions}` |"
            )
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    series_path = Path(args.series_json)
    series = json.loads(series_path.read_text(encoding="utf-8"))
    report = render_report(series, parse_csv(args.objectives))
    if args.output:
        Path(args.output).write_text(report + "\n", encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
