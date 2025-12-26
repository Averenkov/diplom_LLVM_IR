#!/usr/bin/env bash
set -euo pipefail

SRC="${1:-main.cpp}"

if [[ ! -f "$SRC" ]]; then
  echo "ERROR: source file not found: $SRC" >&2
  echo "Usage: $0 [source.cpp|source.c]" >&2
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "ERROR: Homebrew (brew) not found. Install brew first." >&2
  exit 1
fi

LLVM_PREFIX="$(brew --prefix llvm 2>/dev/null || true)"
if [[ -z "${LLVM_PREFIX}" || ! -d "${LLVM_PREFIX}" ]]; then
  echo "ERROR: brew llvm not found. Install: brew install llvm" >&2
  exit 1
fi

LLVM_BIN="${LLVM_PREFIX}/bin"
LLVM_CMAKE_DIR="${LLVM_PREFIX}/lib/cmake/llvm"

CLANG="${LLVM_BIN}/clang"
CLANGXX="${LLVM_BIN}/clang++"
OPT="${LLVM_BIN}/opt"

if [[ ! -x "$OPT" ]]; then
  echo "ERROR: opt not found at: $OPT" >&2
  exit 1
fi

echo "[1/3] Building bitcode (.bc) from: ${SRC}"
BASE="$(basename "$SRC")"
NAME="${BASE%.*}"
BC="${NAME}.bc"

case "$SRC" in
  *.c)   "$CLANG"   -O0 -emit-llvm -c "$SRC" -o "$BC" ;;
  *.cc|*.cpp|*.cxx) "$CLANGXX" -O0 -emit-llvm -c "$SRC" -o "$BC" ;;
  *)
    echo "ERROR: unsupported extension: $SRC (need .c/.cpp)" >&2
    exit 1
    ;;
esac
ls -lh "$BC"

echo
echo "[2/3] Building LLVM pass plugin (CMake)"
rm -rf build
cmake -S . -B build \
  -DLLVM_DIR="$LLVM_CMAKE_DIR" \
  -DCMAKE_C_COMPILER="$CLANG" \
  -DCMAKE_CXX_COMPILER="$CLANGXX"
cmake --build build -j

PLUGIN=""
if [[ -f build/Top20BiggestFuncs.dylib ]]; then
  PLUGIN="build/Top20BiggestFuncs.dylib"
elif [[ -f build/Top20BiggestFuncs.so ]]; then
  PLUGIN="build/Top20BiggestFuncs.so"
else
  PLUGIN="$(find build -maxdepth 2 -type f \( -name 'Top20BiggestFuncs.dylib' -o -name 'Top20BiggestFuncs.so' \) | head -n 1 || true)"
fi

if [[ -z "$PLUGIN" || ! -f "$PLUGIN" ]]; then
  echo "ERROR: plugin not found after build (expected Top20BiggestFuncs.dylib/.so)" >&2
  exit 1
fi

echo "Plugin: $PLUGIN"

echo
echo "[3/3] Running opt with plugin on: $BC"
"$OPT" -load-pass-plugin "./$PLUGIN" -passes=top20-biggest-funcs -disable-output "$BC"
