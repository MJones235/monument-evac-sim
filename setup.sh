#!/usr/bin/env bash
# Setup script for monument-evacuation.
# Run once to create the virtual environment and install all dependencies.
#
# Usage:
#   bash setup.sh
#
# After setup, activate with:
#   source .venv/bin/activate
# Then run experiments with:
#   python run_experiment.py experiments/E1/config.yaml

set -e

echo "=== monument-evacuation setup ==="

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "Installing evacusim framework (editable)..."
pip install -e /home/michael/evacusim -q

echo "Copying credentials template..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "  --> Edit .env and add your Azure OpenAI credentials before running."
fi

echo ""
echo "=== Setup complete ==="
echo "Activate with:  source .venv/bin/activate"
echo "Run E1 with:    python run_experiment.py experiments/E1/config.yaml"
