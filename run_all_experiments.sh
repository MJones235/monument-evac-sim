#!/usr/bin/env bash
# Run all five Monument Station evacuation experiments.
# Each experiment is run RUNS_PER_EXPERIMENT times (default 3).
#
# Usage:
#   ./run_all_experiments.sh            # 3 runs per experiment
#   ./run_all_experiments.sh 5          # 5 runs per experiment
#   EXPERIMENTS="E1 E2" ./run_all_experiments.sh  # specific experiments only

set -euo pipefail

RUNS=${1:-3}
EXPERIMENTS=${EXPERIMENTS:-"E1 E2 E3 E4 E5"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

# Activate virtualenv if present and not already active
if [[ -z "${VIRTUAL_ENV:-}" && -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
fi

echo "=============================================="
echo " Monument Station Evacuation — Batch Runner"
echo " Experiments : $EXPERIMENTS"
echo " Runs each   : $RUNS"
echo " Start time  : $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="
echo

overall_start=$(date +%s)
total_runs=0
failed_runs=0

for exp in $EXPERIMENTS; do
    config="experiments/${exp}/config.yaml"
    if [[ ! -f "$config" ]]; then
        echo "⚠️  Skipping $exp — config not found at $config"
        continue
    fi

    echo "----------------------------------------------"
    echo " Experiment $exp  (${RUNS} run(s))"
    echo "----------------------------------------------"

    for ((i = 1; i <= RUNS; i++)); do
        echo "  ▶  $exp  run $i / $RUNS  —  $(date '+%H:%M:%S')"
        run_start=$(date +%s)

        if python run_experiment.py "$config" --no-viewer --no-spatial-viewer; then
            run_end=$(date +%s)
            elapsed=$(( run_end - run_start ))
            echo "  ✔  $exp  run $i  completed in ${elapsed}s"
        else
            run_end=$(date +%s)
            elapsed=$(( run_end - run_start ))
            echo "  ✘  $exp  run $i  FAILED after ${elapsed}s (exit code $?)"
            (( failed_runs++ )) || true
        fi
        (( total_runs++ )) || true
        echo
    done
done

overall_end=$(date +%s)
total_elapsed=$(( overall_end - overall_start ))
total_mins=$(( total_elapsed / 60 ))
total_secs=$(( total_elapsed % 60 ))

echo "=============================================="
echo " Batch complete"
echo " Total runs   : $total_runs"
echo " Failed runs  : $failed_runs"
echo " Total time   : ${total_mins}m ${total_secs}s"
echo " End time     : $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================="

if (( failed_runs > 0 )); then
    exit 1
fi
