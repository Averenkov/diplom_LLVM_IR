#!/usr/bin/env python3
"""Compare multiple subset_autotune.json experiment runs."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare subset_autotune.json files across strategies."
    )
    parser.add_argument(
        "runs",
        nargs="+",
        help="Paths to subset_autotune.json files.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Optional directory for comparison CSV/Markdown files.",
    )
    return parser.parse_args()


def load_run(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    config = payload.get("config", {})
    strategy = config.get("strategy") or path.parent.name
    return {
        "path": path,
        "strategy": strategy,
        "config": config,
        "model": payload.get("model"),
        "results": payload.get("results", []),
    }


def as_float(value: Any) -> float:
    return float(value) if value is not None and value != "" else 0.0


def summarize_run(run: dict[str, Any]) -> dict[str, Any]:
    improvements = [as_float(item.get("improvement")) for item in run["results"]]
    improved = [value for value in improvements if value > 0]
    errors = [
        evaluation.get("error", "")
        for item in run["results"]
        for evaluation in item.get("evaluations", [])
        if evaluation.get("error")
    ]
    best_kinds = {}
    for item in run["results"]:
        kind = item.get("best_kind", "")
        best_kinds[kind] = best_kinds.get(kind, 0) + 1

    return {
        "strategy": run["strategy"],
        "path": str(run["path"]),
        "benchmarks": len(run["results"]),
        "improved": len(improved),
        "avg_improvement": statistics.mean(improvements) if improvements else 0.0,
        "median_improvement": statistics.median(improvements) if improvements else 0.0,
        "min_improvement": min(improvements) if improvements else 0.0,
        "max_improvement": max(improvements) if improvements else 0.0,
        "error_count": len(errors),
        "best_kind_counts": json.dumps(best_kinds, sort_keys=True),
    }


def per_benchmark_rows(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_benchmark: dict[str, dict[str, Any]] = {}
    for run in runs:
        for item in run["results"]:
            benchmark_uri = item["benchmark_uri"]
            row = by_benchmark.setdefault(
                benchmark_uri,
                {
                    "suite": item.get("suite", ""),
                    "benchmark_uri": benchmark_uri,
                },
            )
            prefix = run["strategy"]
            row[f"{prefix}_best_kind"] = item.get("best_kind", "")
            row[f"{prefix}_best_trial"] = item.get("best_trial", "")
            row[f"{prefix}_baseline"] = item.get("baseline_objective", "")
            row[f"{prefix}_best"] = item.get("best_objective", "")
            row[f"{prefix}_improvement"] = item.get("improvement", "")

    rows = []
    for row in by_benchmark.values():
        winner = ""
        winner_improvement: float | None = None
        for run in runs:
            value = row.get(f"{run['strategy']}_improvement", "")
            if value == "":
                continue
            improvement = as_float(value)
            if winner_improvement is None or improvement > winner_improvement:
                winner = run["strategy"]
                winner_improvement = improvement
        row["winner"] = winner
        row["winner_improvement"] = winner_improvement if winner_improvement is not None else ""
        rows.append(row)
    return sorted(rows, key=lambda item: item["benchmark_uri"])


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def render_markdown(
    summaries: list[dict[str, Any]],
    benchmark_rows: list[dict[str, Any]],
    runs: list[dict[str, Any]],
) -> str:
    lines = [
        "# Autotune Run Comparison",
        "",
        "## Strategy Summary",
        "",
        "| Strategy | Benchmarks | Improved | Avg improvement | Median | Min | Max | Errors |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in summaries:
        lines.append(
            f"| {item['strategy']} | {item['benchmarks']} | {item['improved']} | "
            f"{fmt(item['avg_improvement'])} | {fmt(item['median_improvement'])} | "
            f"{fmt(item['min_improvement'])} | {fmt(item['max_improvement'])} | "
            f"{item['error_count']} |"
        )

    strategy_names = [run["strategy"] for run in runs]
    lines.extend(
        [
            "",
            "## Per-Benchmark Winner",
            "",
            "| Suite | Benchmark | Winner | Winner improvement | "
            + " | ".join(f"{name} improvement" for name in strategy_names)
            + " |",
            "| --- | --- | --- | ---: | "
            + " | ".join("---:" for _ in strategy_names)
            + " |",
        ]
    )
    for row in benchmark_rows:
        improvements = [
            fmt(as_float(row.get(f"{name}_improvement", 0.0)))
            if row.get(f"{name}_improvement", "") != ""
            else ""
            for name in strategy_names
        ]
        lines.append(
            f"| {row['suite']} | `{row['benchmark_uri']}` | {row['winner']} | "
            f"{fmt(row['winner_improvement'])} | "
            + " | ".join(improvements)
            + " |"
        )

    lines.extend(["", "## Inputs", ""])
    for run in runs:
        config = run["config"]
        lines.append(
            f"- `{run['strategy']}`: `{run['path']}` "
            f"(trials={config.get('trials')}, steps={config.get('steps')}, "
            f"seed={config.get('seed')})"
        )
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> int:
    args = parse_args()
    runs = [load_run(Path(path)) for path in args.runs]
    summaries = [summarize_run(run) for run in runs]
    benchmark_rows = per_benchmark_rows(runs)
    report = render_markdown(summaries, benchmark_rows, runs)

    print(report)
    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        write_csv(out_dir / "autotune_strategy_summary.csv", summaries)
        write_csv(out_dir / "autotune_benchmark_comparison.csv", benchmark_rows)
        (out_dir / "autotune_comparison.md").write_text(
            report + "\n", encoding="utf-8"
        )
        print(f"\nWrote: {out_dir / 'autotune_strategy_summary.csv'}")
        print(f"Wrote: {out_dir / 'autotune_benchmark_comparison.csv'}")
        print(f"Wrote: {out_dir / 'autotune_comparison.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
