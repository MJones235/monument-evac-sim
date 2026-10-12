#!/usr/bin/env bash
# Create the virtual environment and install the engine and the study.
#
# Usage:
#   bash setup.sh [PATH_TO_EVACUSIM]     # default: ../evacusim
#
# evacusim (the simulation engine) is installed editable from a local clone,
# then this study package without re-resolving evacusim from GitHub.
set -euo pipefail

EVACUSIM="${1:-$(dirname "$(pwd)")/evacusim}"
if [ ! -f "$EVACUSIM/pyproject.toml" ]; then
    echo "evacusim not found at $EVACUSIM; clone it or pass its path:" >&2
    echo "  git clone git@github.com:MJones235/llm-evacuation-sim.git ../evacusim" >&2
    exit 1
fi

[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -e "$EVACUSIM[dev]"
pip install -q --no-deps -e ".[dev]"
pip install -q pandas matplotlib   # study-only dependencies (see pyproject.toml)
pre-commit install

[ -f .env ] || { cp .env.example .env; echo "Edit .env to use the LLM engine."; }
echo "Done. Activate with: source .venv/bin/activate   then try: monument --help"
