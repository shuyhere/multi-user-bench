#!/usr/bin/env bash
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Batch submission script for controlled experiments
# Usgae: ./batch_submit_experiments.sh

DATA_DIR="${PROJECT_DIR}/data/scenarios/meeting_scheduling/data_builder/controlled_exp_large"
SCENARIO="meeting_scheduling"
USER_MODEL="deepseek/deepseek-chat-v3-0324"
MAX_TURNS=10

echo "Submitting evaluation jobs for all datasets in $DATA_DIR..."

for data_file in "$DATA_DIR"/*.jsonl; do
    if [[ -f "$data_file" ]]; then
        echo "Processing: $data_file"
        bash scripts/submit_eval.sh \
            --scenario "$SCENARIO" \
            --data "$data_file" \
            --user-model "$USER_MODEL" \
            --max-turns "$MAX_TURNS"
        # Add a small delay regarding scheduler
        sleep 1
    fi
done

echo "All batch jobs submitted."
