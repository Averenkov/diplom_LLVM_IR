#!/usr/bin/env python3
"""Analyze a fixed CompilerGym benchmark set with the local LLVM pass."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from compile_gym_bridge import (
    build_plugin,
    configure_compiler_gym_dirs,
    configure_runtime_library_path,
    ensure_compiler_gym,
    locate_opt,
    locate_plugin,
    run_pass,
    write_bitcode,
)


SUMMARY_FIELDS = (
    "suite",
    "benchmark_uri",
    "status",
    "elapsed_sec",
    "functions_defined",
    "total_ir_insts",
    "selected_count",
    "selected_ir_insts",
    "selected_share_percent",
    "dominant_function_share_percent",
    "top_3_share_percent",
    "top_5_share_percent",
    "mean_function_size",
    "median_function_size",
    "stddev_function_size",
    "size_concentration_hhi",
    "size_gini",
    "error",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Top20BiggestFuncs over a CSV benchmark set."
    )
    parser.add_argument(
        "--benchmark-file",
        required=True,
        help="CSV file with `suite` and `benchmark_uri` columns.",
    )
    parser.add_argument(
        "--env",
        default="llvm-v0",
        help="CompilerGym environment id (default: %(default)s).",
    )
    parser.add_argument(
        "--fraction",
        type=float,
        default=0.20,
        help="Fraction of largest functions selected by the pass.",
    )
    parser.add_argument(
        "--cpp-dir",
        default=str(Path(__file__).resolve().parents[1] / "cpp"),
        help="Path to the C++ pass directory.",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Directory for results. Defaults to experiments/runs/<timestamp>.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional maximum number of CSV rows to analyze.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop after the first failed benchmark.",
    )
    return parser.parse_args()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def make_output_dir(raw: str) -> Path:
    out_dir = Path(raw) if raw else Path("experiments") / "runs" / utc_timestamp()
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def load_rows(path: Path, limit: int = 0) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as inp:
        rows = list(csv.DictReader(inp))
    return rows[:limit] if limit else rows


def flatten_result(
    row: dict[str, str],
    payload: dict[str, Any] | None,
    elapsed_sec: float,
    error: str = "",
) -> dict[str, Any]:
    flat: dict[str, Any] = {
        "suite": row.get("suite", ""),
        "benchmark_uri": row.get("benchmark_uri", ""),
        "status": "ok" if payload else "error",
        "elapsed_sec": round(elapsed_sec, 6),
        "error": error,
    }
    if not payload:
        return flat

    tu_metrics = payload.get("translation_unit_aggregation", {})
    flat.update(
        {
            "functions_defined": payload.get("functions_defined"),
            "total_ir_insts": payload.get("total_ir_insts"),
            "selected_count": payload.get("selected_count"),
            "selected_ir_insts": payload.get("selected_ir_insts"),
            "selected_share_percent": payload.get("selected_share_percent"),
            "dominant_function_share_percent": tu_metrics.get(
                "dominant_function_share_percent"
            ),
            "top_3_share_percent": tu_metrics.get("top_3_share_percent"),
            "top_5_share_percent": tu_metrics.get("top_5_share_percent"),
            "mean_function_size": tu_metrics.get("mean_function_size"),
            "median_function_size": tu_metrics.get("median_function_size"),
            "stddev_function_size": tu_metrics.get("stddev_function_size"),
            "size_concentration_hhi": tu_metrics.get("size_concentration_hhi"),
            "size_gini": tu_metrics.get("size_gini"),
        }
    )
    return flat


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in SUMMARY_FIELDS})


def main() -> int:
    args = parse_args()
    benchmark_file = Path(args.benchmark_file)
    rows = load_rows(benchmark_file, args.limit)
    out_dir = make_output_dir(args.output_dir)

    project_root = Path(__file__).resolve().parents[1]
    cpp_dir = Path(args.cpp_dir).resolve()
    configure_compiler_gym_dirs(project_root)
    configure_runtime_library_path()
    compiler_gym = ensure_compiler_gym()

    build_plugin(cpp_dir)
    plugin_path = locate_plugin(cpp_dir)
    opt_bin = locate_opt()

    results: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    with compiler_gym.make(args.env) as env:
        for index, row in enumerate(rows, start=1):
            benchmark_uri = row["benchmark_uri"]
            print(
                f"[{index}/{len(rows)}] {row.get('suite', '')} {benchmark_uri}",
                flush=True,
            )
            started = time.perf_counter()
            payload: dict[str, Any] | None = None
            error = ""
            try:
                env.reset(benchmark=benchmark_uri)
                bitcode = env.observation["Bitcode"]
                with tempfile.TemporaryDirectory(prefix="benchmark_set_") as tmpdir:
                    workdir = Path(tmpdir)
                    bitcode_path = write_bitcode(bitcode, workdir)
                    output_path = workdir / "top20.json"
                    run_pass(opt_bin, plugin_path, bitcode_path, output_path, args.fraction)
                    payload = json.loads(output_path.read_text(encoding="utf-8"))
                payload["benchmark"] = benchmark_uri
                payload["compiler_gym_env"] = args.env
                payload["suite"] = row.get("suite", "")
            except Exception as exc:  # noqa: BLE001 - keep partial run artifacts.
                error = f"{type(exc).__name__}: {exc}"
                print(f"  ERROR: {error}", flush=True)

            elapsed_sec = time.perf_counter() - started
            results.append(
                {
                    "input": row,
                    "elapsed_sec": elapsed_sec,
                    "error": error,
                    "payload": payload,
                }
            )
            summary_rows.append(flatten_result(row, payload, elapsed_sec, error))

            if error and args.fail_fast:
                break

    successful = sum(1 for item in results if item["payload"])
    report = {
        "created_at_utc": utc_timestamp(),
        "benchmark_file": str(benchmark_file),
        "compiler_gym_env": args.env,
        "fraction": args.fraction,
        "successful_evaluations": successful,
        "failed_evaluations": len(results) - successful,
        "results": results,
    }

    (out_dir / "benchmark_set_results.json").write_text(
        json.dumps(report, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    write_csv(out_dir / "benchmark_set_summary.csv", summary_rows)
    print(f"Wrote: {out_dir / 'benchmark_set_results.json'}")
    print(f"Wrote: {out_dir / 'benchmark_set_summary.csv'}")

    return 0 if successful else 1


if __name__ == "__main__":
    sys.exit(main())
