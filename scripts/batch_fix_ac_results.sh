#!/bin/bash

# Base directories
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="$PROJECT_DIR/data/scenarios/access_control/test_datasets/controlled_exp_large"
RESULTS_DIR="$PROJECT_DIR/results/access_control"
FIX_SCRIPT="$PROJECT_DIR/scripts/re_evaluate_ac.py"

export PYTHONPATH=$PROJECT_DIR

echo "Starting batch fix for Access Control results..."

# Iterate over dataset directories in results
for dataset_path in "$RESULTS_DIR"/*; do
    if [[ -d "$dataset_path" ]]; then
        dataset_name=$(basename "$dataset_path")
        data_file="$DATA_DIR/${dataset_name}.jsonl"
        
        if [[ -f "$data_file" ]]; then
            echo "Found matching dataset: $dataset_name"
            
            # Iterate over model directories
            for model_path in "$dataset_path"/*; do
                if [[ -d "$model_path" ]]; then
                    model_name=$(basename "$model_path")
                    # Filter for specific models
                    if [[ "$model_name" == "anthropic-claude-sonnet-4.5" ]] || \
                       [[ "$model_name" == "google-gemini-3-pro-preview" ]] || \
                       [[ "$model_name" == "openai-gpt-5.2" ]]; then
                        
                        # Find result jsonl files
                        for result_file in "$model_path"/*.jsonl; do
                            if [[ -f "$result_file" ]]; then
                                echo "  Fixing: $model_name/$(basename "$result_file")"
                                python "$FIX_SCRIPT" --data "$data_file" --result "$result_file"
                            fi
                        done
                    fi
                fi
            done
        else
            echo "Skipping $dataset_name (No matching data file in $DATA_DIR)"
        fi
    fi
done

echo "Batch fix complete."
