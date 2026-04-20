#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MINIFORGE_DIR="${PROJECT_ROOT}/.miniforge"
ENV_NAME="cgym-py310"
ENV_PYTHON="${MINIFORGE_DIR}/envs/${ENV_NAME}/bin/python"
ENV_PIP="${MINIFORGE_DIR}/envs/${ENV_NAME}/bin/pip"
ENV_LIB_DIR="${MINIFORGE_DIR}/envs/${ENV_NAME}/lib"
MINIFORGE_INSTALLER="/tmp/Miniforge3-Linux-x86_64.sh"
NCURSES_ARCHIVE="/tmp/ncurses-5.9-701.tar.bz2"
NCURSES_EXTRACT_DIR="/tmp/ncurses-5.9-701"

download_file() {
  local url="$1"
  local out="$2"
  if [[ -f "$out" ]]; then
    return 0
  fi
  curl -L "$url" -o "$out"
}

echo "[1/5] Installing Miniforge into ${MINIFORGE_DIR}"
if [[ ! -x "${MINIFORGE_DIR}/bin/mamba" ]]; then
  download_file \
    "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh" \
    "${MINIFORGE_INSTALLER}"
  bash "${MINIFORGE_INSTALLER}" -b -p "${MINIFORGE_DIR}"
fi

echo "[2/5] Creating ${ENV_NAME}"
if [[ ! -x "${ENV_PYTHON}" ]]; then
  "${MINIFORGE_DIR}/bin/mamba" create -y -n "${ENV_NAME}" python=3.10 pip
fi

echo "[3/5] Pinning toolchain for CompilerGym 0.2.5"
"${MINIFORGE_DIR}/bin/mamba" install -y -n "${ENV_NAME}" \
  "pip<24" "setuptools<66" "wheel<0.39" "numpy<2"

echo "[4/5] Installing compiler_gym"
"${ENV_PIP}" install compiler_gym

echo "[5/5] Installing libtinfo.so.5 compatibility shim"
download_file \
  "https://conda.anaconda.org/biobuilds/linux-64/ncurses-5.9-701.tar.bz2" \
  "${NCURSES_ARCHIVE}"
rm -rf "${NCURSES_EXTRACT_DIR}"
mkdir -p "${NCURSES_EXTRACT_DIR}"
tar -xjf "${NCURSES_ARCHIVE}" -C "${NCURSES_EXTRACT_DIR}"
cp "${NCURSES_EXTRACT_DIR}/lib/libncurses.so.5" "${ENV_LIB_DIR}/libtinfo.so.5"

echo
echo "CompilerGym environment is ready."
echo "Run it with:"
echo "  ${ENV_PYTHON} ${PROJECT_ROOT}/python/compile_gym_bridge.py --benchmark cbench-v1/qsort --output result.json"
