#!/usr/bin/env bash

# Unified batch submission script for ALL four Muses-bench scenarios
# Usage: 
#   ./scripts/submit_all_scenarios.sh --model /path/to/vllm/model [--lora-path /path/to/lora] [--debug]
#   ./scripts/submit_all_scenarios.sh --models "openai/gpt-4o-mini,anthropic/claude-3-5-sonnet"

set -euo pipefail

# --- Parse Arguments ---
MODEL_PATH=""
# MODEL_PATH="<PROJECT_DIR>/multiuser_llm_training/training/checkpoints/qwen3-4b-multiuser-full_mix"
# LORA_PATH="<PROJECT_DIR>/multiuser_llm_training/training/checkpoints/qwen3-4b-it-2507-multiuser-lora-mix_new"
LORA_PATH=""
DEBUG_MODE=false
CUSTOM_MODELS="openai/gpt-5.2,anthropic/claude-sonnet-4.5,google/gemini-3-pro-preview"
PROVIDER=""  # Default to API models
USER_MODEL="deepseek/deepseek-chat"
USE_TRAINING_FORMAT=false

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --model <path>         Path to vLLM model (sets provider to vllm)"
    echo "  --models <list>        Comma-separated list of API models"
    echo "  --lora-path <path>     Path to LoRA adapter (optional, for vllm)"
    echo "  --user-model <model>   Model for simulated users (default: deepseek/deepseek-chat)"
    echo "  --debug                Run in debug mode (first 3 samples only)"
    echo "  --use-training-format  Use @ style format (training format) instead of XML tags"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Test vLLM model on all scenarios"
    echo "  $0 --model /path/to/models/qwen3-4b"
    echo ""
    echo "  # Test vLLM model with LoRA"
    echo "  $0 --model /path/to/models/qwen3-4b --lora-path /path/to/lora"
    echo ""
    echo "  # Test specific API models"
    echo "  $0 --models \"openai/gpt-4o-mini,anthropic/claude-3-5-sonnet\""
    echo ""
    echo "  # Debug mode with vLLM"
    echo "  $0 --model /path/to/model --debug"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL_PATH="$2"
            PROVIDER="vllm"
            shift 2
            ;;
        --models)
            CUSTOM_MODELS="$2"
            shift 2
            ;;
        --lora-path)
            LORA_PATH="$2"
            shift 2
            ;;
        --user-model)
            USER_MODEL="$2"
            shift 2
            ;;
        --debug)
            DEBUG_MODE=true
            shift
            ;;
        --use-training-format)
            USE_TRAINING_FORMAT=true
            shift
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Validate arguments
if [[ -z "$MODEL_PATH" && -z "$CUSTOM_MODELS" ]]; then
    echo "[INFO] No models specified. Will use the DEFAULT model list defined in submit_eval.sh"
    # echo "Error: Must specify either --model (for vLLM) or --models (for API models)"
    # show_usage
fi

if [[ -n "$MODEL_PATH" && -n "$CUSTOM_MODELS" ]]; then
    echo "Error: Cannot specify both --model and --models"
    show_usage
fi

# --- Configuration ---
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SUBMIT_SCRIPT="$PROJECT_DIR/scripts/submit_eval.sh"

# Build common arguments
COMMON_ARGS=""
if [[ -n "$MODEL_PATH" ]]; then
    COMMON_ARGS="--provider vllm --models $MODEL_PATH"
elif [[ -n "$CUSTOM_MODELS" ]]; then
    COMMON_ARGS="--models $CUSTOM_MODELS"
fi

if [[ -n "$LORA_PATH" ]]; then
    COMMON_ARGS="$COMMON_ARGS --lora-path $LORA_PATH"
fi

if [[ -n "$USER_MODEL" ]]; then
    COMMON_ARGS="$COMMON_ARGS --user-model $USER_MODEL"
fi

if $DEBUG_MODE; then
    COMMON_ARGS="$COMMON_ARGS --debug"
fi

if $USE_TRAINING_FORMAT; then
    COMMON_ARGS="$COMMON_ARGS --use-training-format"
fi

echo "========================================="
echo "Muses-Bench: Submitting All Scenarios"
echo "========================================="
echo "Provider: $PROVIDER"
if [[ -n "$MODEL_PATH" ]]; then
    echo "vLLM Model: $MODEL_PATH"
fi
if [[ -n "$CUSTOM_MODELS" ]]; then
    echo "API Models: $CUSTOM_MODELS"
fi
if [[ -n "$LORA_PATH" ]]; then
    echo "LoRA Path: $LORA_PATH"
fi
echo "User Model: $USER_MODEL"
echo "Debug Mode: $DEBUG_MODE"
echo "Training Format: $USE_TRAINING_FORMAT"
echo "========================================="
echo ""

# Counter for total jobs
TOTAL_JOBS=0

# --- Scenario 1: Shared Queue ---
# echo "📋 [1/4] Submitting Shared Queue scenarios..."
# DATA_FILE="$PROJECT_DIR/data/scenarios/shared_llm_queue/queue_testset_2_20.jsonl"
# if [[ -f "$DATA_FILE" ]]; then
#     bash "$SUBMIT_SCRIPT" \
#         --scenario shared_queue \
#         --data "$DATA_FILE" \
#         $COMMON_ARGS
#     TOTAL_JOBS=$((TOTAL_JOBS + 1))
#     sleep 1
# else
#     echo "⚠️  Warning: $DATA_FILE not found, skipping"
# fi
# echo ""

# --- Scenario 2: Access Control ---
echo "🔐 [2/4] Submitting Access Control scenarios..."
AC_DIR="$PROJECT_DIR/data/scenarios/access_control/test_datasets/controlled_exp_large"
if [[ -d "$AC_DIR" ]]; then
    for data_file in "$AC_DIR"/*.jsonl; do
        if [[ -f "$data_file" ]]; then
            echo "  Processing: $(basename "$data_file")"
            bash "$SUBMIT_SCRIPT" \
                --scenario access_control \
                --data "$data_file" \
                --max-turns 10 \
                $COMMON_ARGS
            TOTAL_JOBS=$((TOTAL_JOBS + 1))
            sleep 1
        fi
    done
else
    echo "⚠️  Warning: $AC_DIR not found, skipping"
fi
echo ""

# --- Scenario 3: Meeting Scheduling ---
# echo "📅 [3/4] Submitting Meeting Scheduling scenarios..."
# MS_DIR="<PROJECT_DIR>/data/scenarios/meeting_scheduling/data_builder/controlled_exp_large"
# if [[ -d "$MS_DIR" ]]; then
#     for data_file in "$MS_DIR"/*.jsonl; do
#         if [[ -f "$data_file" ]]; then
#             echo "  Processing: $(basename "$data_file")"
#             # Use max-turns 50 for large-scale scenarios (10-30 users)
#             bash "$SUBMIT_SCRIPT" \
#                 --scenario meeting_scheduling \
#                 --data "$data_file" \
#                 --max-turns 10 \
#                 $COMMON_ARGS
#             TOTAL_JOBS=$((TOTAL_JOBS + 1))
#             sleep 1
#         fi
#     done
# else
#     echo "⚠️  Warning: $MS_DIR not found, skipping"
# fi
# echo ""

# --- Scenario 4: Multi-User Instruction Following ---
# echo "✅ [4/4] Submitting Multi-User Instruction Following scenarios..."
# IF_DIR="$PROJECT_DIR/data/scenarios/multiuser_instruction_following/data_builder/controlled_exp"
# if [[ -d "$IF_DIR" ]]; then
#     for data_file in "$IF_DIR"/*.jsonl; do
#         if [[ -f "$data_file" ]]; then
#             echo "  Processing: $(basename "$data_file")"
#             bash "$SUBMIT_SCRIPT" \
#                 --scenario multiuser_instruction_following \
#                 --data "$data_file" \
#                 --max-turns 1 \
#                 $COMMON_ARGS
#             TOTAL_JOBS=$((TOTAL_JOBS + 1))
#             sleep 1
#         fi
#     done
# else
#     echo "⚠️  Warning: $IF_DIR not found, skipping"
# fi
# echo ""

echo "========================================="
echo "✅ All Scenarios Submitted!"
echo "========================================="
echo "Total jobs submitted: $TOTAL_JOBS"
echo ""
echo "Scenarios covered:"
echo "  1. Shared Queue (Priority-Based Resource Allocation)"
echo "  2. Access Control (Privacy-Preserving)"
echo "  3. Meeting Scheduling (Collaborative)"
echo "  4. Multi-User Instruction Following"
echo ""
echo "Monitor jobs with: squeue -u $USER"
echo "Check logs in: $PROJECT_DIR/logs/"
echo "Results will be in: $PROJECT_DIR/results/"
echo "========================================="
