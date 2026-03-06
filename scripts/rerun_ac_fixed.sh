#!/bin/bash
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Rerun specific models for Access Control with lower parallelism
export MAX_WORKERS=4

MODELS="anthropic/claude-sonnet-4.5,google/gemini-3-pro-preview,openai/gpt-5.2"
DATA_DIR="${PROJECT_DIR}/data/scenarios/access_control/test_datasets/controlled_exp_large"
SUBMIT_SCRIPT="${PROJECT_DIR}/scripts/submit_eval.sh"

echo "Using MAX_WORKERS=$MAX_WORKERS"
echo "Models: $MODELS"

for data_file in "$DATA_DIR"/*.jsonl; do
    if [[ -f "$data_file" ]]; then
        echo "Submitting $(basename "$data_file")..."
        bash "$SUBMIT_SCRIPT" \
            --scenario access_control \
            --data "$data_file" \
            --models "$MODELS" \
            --max-turns 10
            
        sleep 1
    fi
done

echo "Rerun submission complete."
