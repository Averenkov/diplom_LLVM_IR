#!/usr/bin/env python3
"""Materialize selected CompilerGym benchmarks as standalone .bc files."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from compile_gym_bridge import (
    configure_compiler_gym_dirs,
    configure_runtime_library_path,
    ensure_compiler_gym,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read a benchmark-set CSV and write each CompilerGym benchmark's "
            "initial LLVM bitcode to a concrete .bc file."
        )
    )
    parser.add_argument(
        "--benchmark-file",
        required=True,
        help="CSV file with at least `suite` and `benchmark_uri` columns.",
    )
    parser.add_argument(
        "--env",
        default="llvm-v0",
        help="CompilerGym environment id (default: %(default)s).",
    )
    parser.add_argument(
        "--output-dir",
        default="experiments/bitcode",
        help="Directory for materialized .bc files.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional maximum number of rows to materialize.",
    )
    return parser.parse_args()


def safe_filename(uri: str) -> str:
    return uri.removeprefix("benchmark://").replace("/", "__") + ".bc"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as inp:
        return list(csv.DictReader(inp))


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parents[1]
    configure_compiler_gym_dirs(project_root)
    configure_runtime_library_path()
    compiler_gym = ensure_compiler_gym()

    rows = load_rows(Path(args.benchmark_file))
    if args.limit:
        rows = rows[: args.limit]

    output_dir = Path(args.output_dir)
    manifest = []
    output_dir.mkdir(parents=True, exist_ok=True)

    with compiler_gym.make(args.env) as env:
        for index, row in enumerate(rows, start=1):
            benchmark_uri = row["benchmark_uri"]
            suite = row.get("suite", "unknown")
            suite_dir = output_dir / suite
            suite_dir.mkdir(parents=True, exist_ok=True)
            bitcode_path = suite_dir / safe_filename(benchmark_uri)

            print(f"[{index}/{len(rows)}] {benchmark_uri} -> {bitcode_path}", flush=True)
            env.reset(benchmark=benchmark_uri)
            bitcode_path.write_bytes(env.observation["Bitcode"])

            materialized = dict(row)
            materialized["materialized_bc_path"] = str(bitcode_path)
            manifest.append(materialized)

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
