#!/usr/bin/env python3
"""Summarize a benchmark-set analysis run and derive useful subsets."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize benchmark_set_summary.csv and write derived subsets."
    )
    parser.add_argument(
        "summary_csv",
        help="Path to benchmark_set_summary.csv from analyze_benchmark_set.py.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Directory for report/subset files. Defaults to summary CSV directory.",
    )
    parser.add_argument(
        "--min-functions",
        type=int,
        default=2,
        help="Minimum defined functions for the multi-function subset.",
    )
    parser.add_argument(
        "--min-ir",
        type=int,
        default=100,
        help="Minimum total IR instructions for the selected subset.",
    )
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as inp:
        return list(csv.DictReader(inp))


def as_int(row: dict[str, str], key: str) -> int:
    value = row.get(key, "")
    return int(float(value)) if value else 0


def as_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value else 0.0


def fmt(value: float) -> str:
    return f"{value:.2f}"


def write_subset(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "suite",
        "benchmark_uri",
        "functions_defined",
        "total_ir_insts",
        "selected_share_percent",
        "dominant_function_share_percent",
        "top_3_share_percent",
        "size_concentration_hhi",
        "size_gini",
    ]
    with path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def suite_stats(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["suite"]].append(row)

    stats = []
    for suite, items in sorted(grouped.items()):
        ok = [row for row in items if row["status"] == "ok"]
        multi = [row for row in ok if as_int(row, "functions_defined") >= 2]
        ir_values = [as_int(row, "total_ir_insts") for row in ok]
        share_values = [as_float(row, "selected_share_percent") for row in ok]
        stats.append(
            {
                "suite": suite,
                "total": len(items),
                "ok": len(ok),
                "multi_function": len(multi),
                "single_function": len(ok) - len(multi),
                "ir_min": min(ir_values) if ir_values else 0,
                "ir_median": statistics.median(ir_values) if ir_values else 0,
                "ir_max": max(ir_values) if ir_values else 0,
                "selected_share_mean": statistics.mean(share_values)
                if share_values
                else 0.0,
            }
        )
    return stats


def render_report(
    rows: list[dict[str, str]],
    selected_subset: list[dict[str, str]],
    min_functions: int,
    min_ir: int,
) -> str:
    stats = suite_stats(rows)
    top_by_ir = sorted(rows, key=lambda row: as_int(row, "total_ir_insts"), reverse=True)[
        :15
    ]
    top_by_gini = sorted(rows, key=lambda row: as_float(row, "size_gini"), reverse=True)[
        :15
    ]

    lines = [
        "# Benchmark Set Baseline Summary",
        "",
        f"- Total rows: {len(rows)}",
        f"- Successful rows: {sum(1 for row in rows if row['status'] == 'ok')}",
        f"- Derived subset rule: functions >= {min_functions}, total IR >= {min_ir}",
        f"- Derived subset size: {len(selected_subset)}",
        "",
        "## Suite Coverage",
        "",
        "| Suite | Total | OK | Multi-func | Single-func | IR min | IR median | IR max | Avg selected % |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in stats:
        lines.append(
            f"| {item['suite']} | {item['total']} | {item['ok']} | "
            f"{item['multi_function']} | {item['single_function']} | "
            f"{item['ir_min']} | {fmt(float(item['ir_median']))} | "
            f"{item['ir_max']} | {fmt(item['selected_share_mean'])} |"
        )

    lines.extend(
        [
            "",
            "## Largest Translation Units",
            "",
            "| Suite | Benchmark | Functions | Total IR | Selected % | Gini |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in top_by_ir:
        lines.append(
            f"| {row['suite']} | `{row['benchmark_uri']}` | "
            f"{row['functions_defined']} | {row['total_ir_insts']} | "
            f"{fmt(as_float(row, 'selected_share_percent'))} | "
            f"{fmt(as_float(row, 'size_gini'))} |"
        )

    lines.extend(
        [
            "",
            "## Most Concentrated By Gini",
            "",
            "| Suite | Benchmark | Functions | Total IR | Selected % | Gini |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in top_by_gini:
        lines.append(
            f"| {row['suite']} | `{row['benchmark_uri']}` | "
            f"{row['functions_defined']} | {row['total_ir_insts']} | "
            f"{fmt(as_float(row, 'selected_share_percent'))} | "
            f"{fmt(as_float(row, 'size_gini'))} |"
        )

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    summary_path = Path(args.summary_csv)
    out_dir = Path(args.output_dir) if args.output_dir else summary_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(summary_path)
    selected_subset = [
        row
        for row in rows
        if row["status"] == "ok"
        and as_int(row, "functions_defined") >= args.min_functions
        and as_int(row, "total_ir_insts") >= args.min_ir
    ]

    report = render_report(rows, selected_subset, args.min_functions, args.min_ir)
    (out_dir / "benchmark_set_report.md").write_text(report + "\n", encoding="utf-8")
    write_subset(out_dir / "benchmark_set_multifunction.csv", selected_subset)
    (out_dir / "benchmark_set_suite_stats.json").write_text(
        json.dumps(suite_stats(rows), indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    print(report)
    print(f"\nWrote: {out_dir / 'benchmark_set_report.md'}")
    print(f"Wrote: {out_dir / 'benchmark_set_multifunction.csv'}")
    print(f"Wrote: {out_dir / 'benchmark_set_suite_stats.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
