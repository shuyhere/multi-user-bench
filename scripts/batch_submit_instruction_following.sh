#!/usr/bin/env bash
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Batch submission script for Multi-User Instruction Following
# Usage: ./scripts/batch_submit_instruction_following.sh

# Directory containing the generated benchmark files (aligned and conflict)
DATA_DIR="${PROJECT_DIR}/data/scenarios/multiuser_instruction_following/data_builder/controlled_exp"
SCENARIO="multiuser_instruction_following"

# Custom models to evaluate (comma-separated).
# Leave EMPTY ("") to evaluate on ALL default models defined in submit_eval.sh.
# Example: CUSTOM_MODELS="openai/gpt-4o-mini,anthropic/claude-3-5-sonnet-20241022"
CUSTOM_MODELS=""

echo "Submitting evaluation jobs for Multi-User Instruction Following..."
echo "Data Directory: $DATA_DIR"
echo "Scenario: $SCENARIO"
if [[ -n "$CUSTOM_MODELS" ]]; then
    echo "Models: $CUSTOM_MODELS"
else
    echo "Models: All default models (from submit_eval.sh)"
fi

# Check if directory exists
if [[ ! -d "$DATA_DIR" ]]; then
    echo "Error: Data directory not found: $DATA_DIR"
    exit 1
fi

# Iterate over JSONL files in the directory
for data_file in "$DATA_DIR"/*.jsonl; do
    if [[ -f "$data_file" ]]; then
        echo "Processing: $data_file"
        
        # Prepare models flag
        MODELS_FLAG=""
        if [[ -n "$CUSTOM_MODELS" ]]; then
            MODELS_FLAG="--models $CUSTOM_MODELS"
        fi

        # We use submit_eval.sh to dispatch the job
        # Omitting --models argument to use the default list in submit_eval.sh unless CUSTOM_MODELS is set
        bash scripts/submit_eval.sh \
            --scenario "$SCENARIO" \
            --data "$data_file" \
            --max-turns 1 \
            $MODELS_FLAG
            
        # Add a small delay regarding scheduler
        sleep 1
    fi
done

echo "All batch jobs submitted."
