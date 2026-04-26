#!/usr/bin/env python3
"""Run the local LLVM pass on a CompilerGym LLVM state."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply the local Top20BiggestFuncs pass to a CompilerGym benchmark."
    )
    parser.add_argument(
        "--benchmark",
        default="cbench-v1/qsort",
        help="CompilerGym benchmark URI (default: %(default)s)",
    )
    parser.add_argument(
        "--env",
        default="llvm-v0",
        help="CompilerGym environment id (default: %(default)s)",
    )
    parser.add_argument(
        "--actions",
        default="",
        help="Comma-separated list of action ids to apply before analysis.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Path to write pass JSON output. If omitted, a temp file is used.",
    )
    parser.add_argument(
        "--fraction",
        type=float,
        default=0.20,
        help="Fraction of largest functions to select (default: %(default)s)",
    )
    parser.add_argument(
        "--cpp-dir",
        default=str(Path(__file__).resolve().parents[1] / "cpp"),
        help="Path to the C++ pass directory (default: %(default)s)",
    )
    return parser.parse_args()


def ensure_compiler_gym():
    try:
        import compiler_gym  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "compiler_gym is not installed. Install it with: pip install compiler_gym"
        ) from exc
    return compiler_gym


def parse_actions(raw: str) -> list[int]:
    if not raw.strip():
        return []
    return [int(part.strip()) for part in raw.split(",") if part.strip()]


def build_plugin(cpp_dir: Path) -> None:
    subprocess.run(["bash", "run.sh", "--build-only"], cwd=cpp_dir, check=True)


def locate_plugin(cpp_dir: Path) -> Path:
    for candidate in (
        cpp_dir / "build" / "Top20BiggestFuncs.so",
        cpp_dir / "build" / "Top20BiggestFuncs.dylib",
    ):
        if candidate.is_file():
            return candidate
    raise SystemExit("LLVM pass plugin was not built successfully.")


def locate_opt() -> str:
    from shutil import which

    for name in ("opt", "opt-18", "opt-17", "opt-16", "opt-15", "opt-14", "opt-13"):
        path = which(name)
        if path:
            return path
    raise SystemExit("opt was not found in PATH.")


def write_bitcode(bitcode: bytes, workdir: Path) -> Path:
    bitcode_path = workdir / "compiler_gym_state.bc"
    bitcode_path.write_bytes(bitcode)
    return bitcode_path


def run_pass(
    opt_bin: str,
    plugin_path: Path,
    bitcode_path: Path,
    output_path: Path,
    fraction: float,
) -> None:
    cmd = [
        opt_bin,
        f"-load-pass-plugin={plugin_path}",
        "-passes=top20-biggest-funcs",
        "-disable-output",
        f"-top-fraction={fraction}",
        f"-top20-output={output_path}",
        str(bitcode_path),
    ]
    subprocess.run(cmd, check=True)


def configure_compiler_gym_dirs(project_root: Path) -> None:
    cache_root = project_root / ".compiler_gym"
    cache_dir = cache_root / "cache"
    site_data_dir = cache_root / "site_data"
    transient_dir = cache_root / "transient"

    for path in (cache_dir, site_data_dir, transient_dir):
        path.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("COMPILER_GYM_CACHE", str(cache_dir))
    os.environ.setdefault("COMPILER_GYM_SITE_DATA", str(site_data_dir))
    os.environ.setdefault("COMPILER_GYM_TRANSIENT_CACHE", str(transient_dir))


def configure_runtime_library_path() -> None:
    python_exe = Path(sys.executable).resolve()
    env_lib = python_exe.parent.parent / "lib"

    if env_lib.is_dir():
        libtinfo5 = env_lib / "libtinfo.so.5"
        libtinfo6 = env_lib / "libtinfo.so.6"
        if not libtinfo5.exists() and libtinfo6.exists():
            libtinfo5.symlink_to(libtinfo6.name)

        ld_library_path = os.environ.get("LD_LIBRARY_PATH", "")
        paths = [str(env_lib)]
        if ld_library_path:
            paths.append(ld_library_path)
        os.environ["LD_LIBRARY_PATH"] = ":".join(paths)


def analyze_benchmark(
    benchmark: str,
    env_name: str = "llvm-v0",
    actions: list[int] | None = None,
    fraction: float = 0.20,
    cpp_dir: Path | None = None,
    output_path: Path | None = None,
    rebuild_plugin: bool = True,
) -> dict[str, Any]:
    resolved_cpp_dir = (
        cpp_dir.resolve()
        if cpp_dir is not None
        else Path(__file__).resolve().parents[1] / "cpp"
    )
    project_root = resolved_cpp_dir.parent
    configure_compiler_gym_dirs(project_root)
    configure_runtime_library_path()
    compiler_gym = ensure_compiler_gym()

    if rebuild_plugin:
        build_plugin(resolved_cpp_dir)
    plugin_path = locate_plugin(resolved_cpp_dir)
    opt_bin = locate_opt()
    resolved_actions = actions or []

    with compiler_gym.make(env_name, benchmark=benchmark) as env:
        env.reset()
        if resolved_actions:
            env.multistep(resolved_actions)
        bitcode = env.observation["Bitcode"]

    with tempfile.TemporaryDirectory(prefix="compile_gym_bridge_") as tmpdir:
        workdir = Path(tmpdir)
        bitcode_path = write_bitcode(bitcode, workdir)
        final_output = output_path or (workdir / "top20.json")
        run_pass(opt_bin, plugin_path, bitcode_path, final_output, fraction)
        payload = json.loads(final_output.read_text(encoding="utf-8"))

    payload["benchmark"] = benchmark
    payload["compiler_gym_env"] = env_name
    payload["actions"] = resolved_actions
    return payload


def main() -> int:
    args = parse_args()
    payload = analyze_benchmark(
        benchmark=args.benchmark,
        env_name=args.env,
        actions=parse_actions(args.actions),
        fraction=args.fraction,
        cpp_dir=Path(args.cpp_dir),
        output_path=Path(args.output).resolve() if args.output else None,
    )

    print(json.dumps(payload, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
