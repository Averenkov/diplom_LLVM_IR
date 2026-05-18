#!/usr/bin/env python3
"""Build a reproducible stratified benchmark subset for autotuning."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_FIELDS = [
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
DEFAULT_SUITE_QUOTAS = "chstone=6,mibench=6,npb=3,opencv=6,tensorflow=6"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a stratified multi-function benchmark subset."
    )
    parser.add_argument(
        "input_csv",
        help="benchmark_set_summary.csv or benchmark_set_multifunction.csv.",
    )
    parser.add_argument(
        "--output-csv",
        default="experiments/benchmark_sets/autotune_stratified_30.csv",
        help="Path for the generated subset CSV.",
    )
    parser.add_argument(
        "--manifest",
        default="",
        help="Optional JSON manifest path. Defaults to <output-csv>.manifest.json.",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=30,
        help="Total subset size after filling suite quotas.",
    )
    parser.add_argument(
        "--suite-quotas",
        default=DEFAULT_SUITE_QUOTAS,
        help="Comma-separated minimum per-suite quotas, e.g. chstone=6,opencv=6.",
    )
    parser.add_argument(
        "--sort-by",
        default="total_ir_insts",
        help="Metric used to rank candidates within each suite and for fill rows.",
    )
    parser.add_argument(
        "--min-functions",
        type=int,
        default=2,
        help="Minimum defined functions required for a candidate row.",
    )
    parser.add_argument(
        "--min-ir",
        type=int,
        default=100,
        help="Minimum total IR instructions required for a candidate row.",
    )
    return parser.parse_args()


def parse_quotas(raw: str) -> dict[str, int]:
    quotas: dict[str, int] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        suite, sep, count = item.partition("=")
        if not sep:
            raise ValueError(f"Invalid suite quota: {item}")
        quotas[suite.strip()] = int(count)
    return quotas


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as inp:
        return list(csv.DictReader(inp))


def as_int(row: dict[str, str], key: str) -> int:
    value = row.get(key, "")
    return int(float(value)) if value else 0


def as_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    return float(value) if value else 0.0


def candidate_rows(
    rows: list[dict[str, str]],
    min_functions: int,
    min_ir: int,
) -> list[dict[str, str]]:
    candidates = []
    for row in rows:
        if row.get("status", "ok") != "ok":
            continue
        if as_int(row, "functions_defined") < min_functions:
            continue
        if as_int(row, "total_ir_insts") < min_ir:
            continue
        candidates.append(row)
    return candidates


def select_rows(
    candidates: list[dict[str, str]],
    quotas: dict[str, int],
    size: int,
    sort_by: str,
) -> list[dict[str, str]]:
    ranked = sorted(candidates, key=lambda row: as_float(row, sort_by), reverse=True)
    selected: list[dict[str, str]] = []
    seen: set[str] = set()

    for suite, quota in quotas.items():
        suite_rows = [row for row in ranked if row.get("suite", "") == suite]
        for row in suite_rows[:quota]:
            selected.append(row)
            seen.add(row["benchmark_uri"])

    for row in ranked:
        if len(selected) >= size:
            break
        if row["benchmark_uri"] not in seen:
            selected.append(row)
            seen.add(row["benchmark_uri"])

    return selected[:size]


def write_subset(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=DEFAULT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in DEFAULT_FIELDS})


def write_manifest(
    path: Path,
    args: argparse.Namespace,
    quotas: dict[str, int],
    candidates: list[dict[str, str]],
    selected: list[dict[str, str]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "input_csv": args.input_csv,
        "output_csv": args.output_csv,
        "size": args.size,
        "suite_quotas": quotas,
        "sort_by": args.sort_by,
        "min_functions": args.min_functions,
        "min_ir": args.min_ir,
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "candidate_suites": dict(Counter(row.get("suite", "") for row in candidates)),
        "selected_suites": dict(Counter(row.get("suite", "") for row in selected)),
        "selected_benchmarks": [row["benchmark_uri"] for row in selected],
    }
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_csv)
    output_path = Path(args.output_csv)
    manifest_path = (
        Path(args.manifest)
        if args.manifest
        else output_path.with_suffix(output_path.suffix + ".manifest.json")
    )
    quotas = parse_quotas(args.suite_quotas)
    rows = load_rows(input_path)
    candidates = candidate_rows(rows, args.min_functions, args.min_ir)
    selected = select_rows(candidates, quotas, args.size, args.sort_by)

    write_subset(output_path, selected)
    write_manifest(manifest_path, args, quotas, candidates, selected)

    print(f"Candidates: {len(candidates)}")
    print(f"Selected: {len(selected)}")
    print(f"Selected suites: {dict(Counter(row.get('suite', '') for row in selected))}")
    print(f"Wrote: {output_path}")
    print(f"Wrote: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
