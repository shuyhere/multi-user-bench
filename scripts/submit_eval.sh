#!/usr/bin/env bash

# Submit batch evaluation jobs for Muses-bench (CPU-only for API models)
# Usage: ./submit_eval.sh --data <data_file> [--debug] [--models model1,model2,...]
set -euo pipefail

# --- Parse Arguments ---
DEBUG_MODE=false
DATA_FILE=""
CUSTOM_MODELS=""
USER_MODEL=""
MAX_TURNS=15
SCENARIO=""
PROVIDER=""
LORA_PATH=""
USE_TRAINING_FORMAT=false

show_usage() {
  echo "Usage: $0 --data <data_file> [--scenario <name>] [--debug] [--models model1,model2,...] [--user-model <model>] [--max-turns <int>] [--provider <name>] [--lora-path <path>]"
  echo ""
  echo "Options:"
  echo "  -d, --data <file>        Path to the JSONL data file (required)"
  echo "  -s, --scenario <name>    Scenario name (default: '')"
  echo "  --debug                  Run in debug mode (first 3 samples only)"
  echo "  -m, --models <list>      Comma-separated list of models (optional)"
  echo "  --user-model <model>     Model to use for simulated users (optional)"
  echo "  --max-turns <int>        Maximum number of turns (default: 15)"
  echo "  --provider <name>        LLM provider (default: openai, use 'vllm' for local models)"
  echo "  --lora-path <path>       Path to LoRA adapter (optional, for vllm)"
  echo ""
  echo "Examples:"
  echo "  $0 --data data/scenarios/access_control/nopersona_single_turn_base.jsonl"
  echo "  $0 --scenario meeting_scheduling --data data/test.jsonl --provider vllm --models /path/to/model"
  echo "  $0 --data data.jsonl --provider vllm --models /base/model --lora-path /lora/adapter"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case $1 in
    -d|--data)
      DATA_FILE="$2"
      shift 2
      ;;
    -s|--scenario)
      SCENARIO="$2"
      shift 2
      ;;
    --debug)
      DEBUG_MODE=true
      shift
      ;;
    -m|--models)
      CUSTOM_MODELS="$2"
      shift 2
      ;;
    --user-model)
      USER_MODEL="$2"
      shift 2
      ;;
    --max-turns)
      MAX_TURNS="$2"
      shift 2
      ;;
    --provider)
      PROVIDER="$2"
      shift 2
      ;;
    --lora-path)
      LORA_PATH="$2"
      shift 2
      ;;
    -h|--help)
      show_usage
      ;;
    --use-training-format)
      USE_TRAINING_FORMAT=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      show_usage
      ;;
  esac
done

# Check required arguments
if [[ -z "$DATA_FILE" ]]; then
  echo "Error: --data argument is required"
  show_usage
fi

if $DEBUG_MODE; then
  echo "[DEBUG MODE] Will run only first 3 samples per model"
fi

# --- Configuration ---
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_ACTIVATE="$PROJECT_DIR/.venv/bin/activate"

# Default list of models to evaluate
# Model names based on: https://doc.zhizengzeng.com/doc-3979947
DEFAULT_MODELS=(
# === OpenAI ===
"openai/gpt-5.1"
"openai/gpt-5-nano"
"openai/gpt-4o-mini"
"openai/gpt-oss-120b"

# === Anthropic/Claude ===
"anthropic/claude-haiku-4.5"
"anthropic/claude-3.5-haiku"


# === Google/Gemini ===
"google/gemini-3-flash-preview"
"google/gemini-2.5-flash"

# === xAI/Grok ===
"x-ai/grok-4.1-fast"
"x-ai/grok-3-mini"

# === DeepSeek ===
"deepseek/deepseek-r1-0528"

# === Qwen/Alibaba ===
"qwen/qwen3-30b-a3b"

# === Meta/Llama ===
"meta-llama/llama-3-70b-instruct"
"meta-llama/llama-3-8b-instruct"

# === Kimi/glm ===
"z-ai/glm-4.5-air"
)

# Use custom models if provided, otherwise use default
if [[ -n "$CUSTOM_MODELS" ]]; then
  IFS=',' read -ra MODELS <<< "$CUSTOM_MODELS"
  echo "Using custom models: ${MODELS[*]}"
else
  MODELS=("${DEFAULT_MODELS[@]}")
fi

# Resources
CPUS=4
MEM=16G
TIME="24:00:00"
GPUS=""
ACCOUNT_CONFIG=""

# Adjust resources for vLLM
if [[ "$PROVIDER" == "vllm" ]]; then
    CPUS=8
    MEM=64G
    GPUS="#SBATCH --gres=gpu:a100:1"
    ACCOUNT_CONFIG="#SBATCH --account=conf-icml-2026.01.29-wangd0d"
    echo "[INFO] vLLM provider detected. requesting GPU and increased memory."
fi

# Extract dataset name from file path (e.g., "nopersona_single_turn_base" from "path/to/nopersona_single_turn_base.jsonl")
DATASET_NAME=$(basename "$DATA_FILE" .jsonl)

# --- Setup directories for this dataset ---
LOG_DIR="$PROJECT_DIR/logs/${SCENARIO}/${DATASET_NAME}"
RESULT_BASE_DIR="$PROJECT_DIR/results/${SCENARIO}/${DATASET_NAME}"

mkdir -p "$LOG_DIR"
mkdir -p "$RESULT_BASE_DIR"

echo ""
echo "========================================"
echo "Evaluation Configuration"
echo "========================================"
echo "Data File: $DATA_FILE"
echo "Dataset Name: $DATASET_NAME"
echo "Scenario: $SCENARIO"
echo "Debug Mode: $DEBUG_MODE"
echo "Log Directory: $LOG_DIR"
echo "Result Base Directory: $RESULT_BASE_DIR"
echo "Models to evaluate: ${#MODELS[@]}"
if [[ -n "$USER_MODEL" ]]; then
  echo "User Model: $USER_MODEL"
fi
echo "Max Turns: $MAX_TURNS"
if [[ -n "$PROVIDER" ]]; then
  echo "Provider: $PROVIDER"
fi
if [[ -n "$LORA_PATH" ]]; then
  echo "LoRA Path: $LORA_PATH"
fi
echo "========================================"
echo ""

submit_job() {
  local model="$1"
  
  # Sanitize model name for file paths (replace / with -)
  local model_safe="${model//\//-}"
  # Also handle paths (if local model) - take basename
  if [[ "$model" == /* ]]; then
      model_safe=$(basename "$model")
  fi
  
  # If LoRA path is provided and exists, use LoRA model name instead
  if [[ -n "$LORA_PATH" ]] && [[ -d "$LORA_PATH" ]]; then
      model_safe=$(basename "$LORA_PATH")
      echo "[INFO] Using LoRA model name for results: $model_safe"
  fi
  
  # Define unique job name
  local job_name="eval-${DATASET_NAME}-${model_safe}"
  
  # Add debug suffix if in debug mode
  local debug_flag=""
  if $DEBUG_MODE; then
    job_name="${job_name}-debug"
    debug_flag="--debug"
  fi
  
  # Prepare arguments
  local user_model_flag=""
  local max_turns_flag=""
  local provider_flag=""
  local lora_flag=""
  local training_format_flag=""
  
  if $USE_TRAINING_FORMAT; then
    training_format_flag="--use-training-format"
  fi

  if [[ "$SCENARIO" != "shared_queue" ]]; then
      if [[ -n "$USER_MODEL" ]]; then
        user_model_flag="--user-model ${USER_MODEL}"
      fi
      max_turns_flag="--max-turns ${MAX_TURNS}"
  fi

  if [[ -n "$PROVIDER" ]]; then
    provider_flag="--provider ${PROVIDER}"
  fi
  
  if [[ -n "$LORA_PATH" ]]; then
    lora_flag="--lora-path ${LORA_PATH}"
  fi
  
  # Create specific result directory for this model
  local result_dir="${RESULT_BASE_DIR}/${model_safe}"
  mkdir -p "$result_dir"
  
  # Output file with timestamp to ensure uniqueness
  local timestamp=$(date +%Y%m%d_%H%M%S)
  local output_file="${result_dir}/results_${timestamp}.jsonl"

  echo "Submitting: $job_name"
  echo "  Model: $model"
  echo "  Output: $output_file"

  # Submit sbatch job
  sbatch <<EOF
#!/usr/bin/env bash
#SBATCH -J ${job_name}
#SBATCH -o ${LOG_DIR}/${job_name}.%j.out
#SBATCH -e ${LOG_DIR}/${job_name}.%j.err
#SBATCH -c ${CPUS}
#SBATCH --mem=${MEM}
#SBATCH --time=${TIME}
#SBATCH --partition=batch
${GPUS}
${ACCOUNT_CONFIG}

set -euo pipefail

# Load environment
source ${VENV_ACTIVATE}
export MAX_WORKERS=${MAX_WORKERS:-8}
cd ${PROJECT_DIR}

# HuggingFace cache settings
export HF_DATASETS_CACHE=${PROJECT_DIR}/.cache/huggingface/datasets
export HF_CACHE_DIR=${PROJECT_DIR}/.cache
export HF_HOME=${PROJECT_DIR}/.cache/huggingface
export HF_HUB_CACHE=${PROJECT_DIR}/.cache/huggingface/hub

echo "========================================"
echo "Job ID: \$SLURM_JOB_ID"
echo "Model: ${model}"
echo "Data: ${DATA_FILE}"
echo "Dataset: ${DATASET_NAME}"
echo "Output: ${output_file}"
echo "Debug Mode: ${DEBUG_MODE}"
echo "Start Time: \$(date)"
echo "========================================"

# Run evaluation
python run.py \
  --scenario ${SCENARIO} \
  --data ${DATA_FILE} \
  --model ${model} \
  ${user_model_flag} \
  ${max_turns_flag} \
  ${provider_flag} \
  ${lora_flag} \
  ${training_format_flag} \
  --output ${output_file} ${debug_flag}

echo "========================================"
echo "End Time: \$(date)"
echo "Results saved to: ${output_file}"
echo "========================================"

EOF
}

# --- Main Loop ---
echo "Submitting jobs for ${#MODELS[@]} models..."
echo ""

for model in "${MODELS[@]}"; do
  submit_job "$model"
  sleep 1 # Mild delay between submissions
done

echo ""
echo "========================================"
echo "All ${#MODELS[@]} jobs submitted."
echo "Logs: $LOG_DIR"
echo "Results: $RESULT_BASE_DIR"
echo "========================================"

