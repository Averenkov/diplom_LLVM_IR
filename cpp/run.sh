#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="main.cpp"
BUILD_ONLY=0
JSON_OUT=""
FRACTION="${TOP_FRACTION:-0.20}"

usage() {
  cat <<EOF
Usage: $0 [source.cpp|source.c] [options]

Options:
  --build-only            Build the LLVM pass plugin and stop.
  --json-out <path>       Write pass results to a JSON file.
  --fraction <value>      Fraction of largest functions to select (default: ${FRACTION}).
  -h, --help              Show this help message.

Environment overrides:
  LLVM_DIR                Path to LLVMConfig.cmake directory.
  LLVM_PREFIX             Prefix that contains bin/ and lib/cmake/llvm/.
  LLVM_CONFIG             Explicit path to llvm-config.
  CLANG, CLANGXX, OPT     Explicit paths to LLVM tools.
EOF
}

find_tool() {
  local base="$1"
  local explicit="${2:-}"
  local candidate

  if [[ -n "$explicit" && -x "$explicit" ]]; then
    printf '%s\n' "$explicit"
    return 0
  fi

  if command -v "$base" >/dev/null 2>&1; then
    command -v "$base"
    return 0
  fi

  for candidate in \
    "$base-18" "$base-17" "$base-16" "$base-15" "$base-14" "$base-13" \
    "/usr/lib/llvm-18/bin/$base" "/usr/lib/llvm-17/bin/$base" \
    "/usr/lib/llvm-16/bin/$base" "/usr/lib/llvm-15/bin/$base" \
    "/usr/lib/llvm-14/bin/$base" "/usr/lib/llvm-13/bin/$base"
  do
    if command -v "$candidate" >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
    if [[ -x "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-only)
      BUILD_ONLY=1
      shift
      ;;
    --json-out)
      JSON_OUT="${2:-}"
      shift 2
      ;;
    --fraction)
      FRACTION="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      echo "ERROR: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      SRC="$1"
      shift
      ;;
  esac
done

if ! command -v cmake >/dev/null 2>&1; then
  echo "ERROR: cmake not found. On Ubuntu install: sudo apt install cmake" >&2
  exit 1
fi

LLVM_CONFIG="$(find_tool llvm-config "${LLVM_CONFIG:-}")" || {
  echo "ERROR: llvm-config not found. On Ubuntu install: sudo apt install llvm-dev" >&2
  exit 1
}

CLANG="${CLANG:-$(find_tool clang "")}" || {
  echo "ERROR: clang not found. On Ubuntu install: sudo apt install clang" >&2
  exit 1
}

CLANGXX="${CLANGXX:-$(find_tool clang++ "")}" || {
  echo "ERROR: clang++ not found. On Ubuntu install: sudo apt install clang" >&2
  exit 1
}

OPT="${OPT:-$(find_tool opt "")}" || {
  echo "ERROR: opt not found. On Ubuntu install: sudo apt install llvm" >&2
  exit 1
}

if [[ -n "${LLVM_PREFIX:-}" && -z "${LLVM_DIR:-}" ]]; then
  LLVM_DIR="${LLVM_PREFIX}/lib/cmake/llvm"
fi

if [[ -z "${LLVM_DIR:-}" ]]; then
  LLVM_DIR="$("$LLVM_CONFIG" --cmakedir)"
fi

if [[ ! -d "$LLVM_DIR" ]]; then
  echo "ERROR: LLVM_DIR does not exist: $LLVM_DIR" >&2
  exit 1
fi

if [[ $BUILD_ONLY -eq 0 ]]; then
  if [[ ! -f "$SRC" ]]; then
    echo "ERROR: source file not found: $SRC" >&2
    usage >&2
    exit 1
  fi
  SRC="$(realpath "$SRC")"
fi

cd "$SCRIPT_DIR"

if [[ $BUILD_ONLY -eq 0 && ! -f "$SRC" ]]; then
  echo "ERROR: resolved source file not found: $SRC" >&2
  usage >&2
  exit 1
fi

echo "Using LLVM_DIR: $LLVM_DIR"
echo "Using clang:    $CLANG"
echo "Using clang++:  $CLANGXX"
echo "Using opt:      $OPT"

echo
echo "[1/3] Building LLVM pass plugin (CMake)"
cmake -S . -B build \
  -DLLVM_DIR="$LLVM_DIR" \
  -DCMAKE_C_COMPILER="$CLANG" \
  -DCMAKE_CXX_COMPILER="$CLANGXX"
cmake --build build -j

PLUGIN=""
if [[ -f build/Top20BiggestFuncs.so ]]; then
  PLUGIN="build/Top20BiggestFuncs.so"
elif [[ -f build/Top20BiggestFuncs.dylib ]]; then
  PLUGIN="build/Top20BiggestFuncs.dylib"
else
  PLUGIN="$(find build -maxdepth 2 -type f \( -name 'Top20BiggestFuncs.so' -o -name 'Top20BiggestFuncs.dylib' \) | head -n 1 || true)"
fi

if [[ -z "$PLUGIN" || ! -f "$PLUGIN" ]]; then
  echo "ERROR: plugin not found after build (expected Top20BiggestFuncs.so/.dylib)" >&2
  exit 1
fi

echo "Plugin: $PLUGIN"

if [[ $BUILD_ONLY -eq 1 ]]; then
  exit 0
fi

echo
echo "[2/3] Building bitcode (.bc) from: ${SRC}"
BASE="$(basename "$SRC")"
NAME="${BASE%.*}"
BC="${NAME}.bc"

case "$SRC" in
  *.c)   "$CLANG"   -O0 -emit-llvm -c "$SRC" -o "$BC" ;;
  *.cc|*.cpp|*.cxx) "$CLANGXX" -O0 -emit-llvm -c "$SRC" -o "$BC" ;;
  *)
    echo "ERROR: unsupported extension: $SRC (need .c/.cc/.cpp/.cxx)" >&2
    exit 1
    ;;
esac
ls -lh "$BC"

echo
echo "[3/3] Running opt with plugin on: $BC"
OPT_ARGS=(
  -load-pass-plugin "./$PLUGIN"
  -passes=top20-biggest-funcs
  -disable-output
  "-top-fraction=${FRACTION}"
)

if [[ -n "$JSON_OUT" ]]; then
  OPT_ARGS+=("-top20-output=${JSON_OUT}")
fi

"$OPT" "${OPT_ARGS[@]}" "$BC"
