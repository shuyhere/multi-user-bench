#!/usr/bin/env bash
set -euo pipefail

# ============================
# User configuration (editable)
# ============================

# Model and Dataset
MODEL_NAME="Qwen/Qwen3-4B-Instruct-2507"
DATASET_PATHS=(
    "<PATH_TO_TRAINING_DATA>/multi_user_training.jsonl"
	# "<PATH_TO_TRAINING_DATA>/capybara_train.jsonl"
)

NEW_MODEL_NAME="qwen3-4b-it-2507-multiuser-full-v2-clean"

# Training Hyperparameters
NUM_EPOCHS=2
BATCH_SIZE=1
GRAD_ACCUM=4
LEARNING_RATE=5e-6
USE_PEFT=false  # Set to 'true' for LoRA training, 'false' for full fine-tuning
# Resources
GPUS="gpu:a100:2"
MEM="256G"
CPUS=10
TIME="12:00:00"
PARTITION="batch"
ACCOUNT="conf-icml-2026.01.29-wangd0d"

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

TRAIN_SCRIPT="$PROJECT_ROOT/training/train.py"
OUTPUT_BASE_DIR="$PROJECT_ROOT/training/checkpoints"
LOG_DIR="$PROJECT_ROOT/training/training_logs"
DEEPSPEED_CONFIG="$PROJECT_ROOT/training/ds_config_stage2_offload.json"

# ============================
# End of user configuration
# ============================

# Ensure directories exist
mkdir -p "$OUTPUT_BASE_DIR"
mkdir -p "$LOG_DIR"

# Generate Job Name and Output Directory
JOB_NAME="multiuser_${NEW_MODEL_NAME}"
OUTPUT_DIR="${OUTPUT_BASE_DIR}/${NEW_MODEL_NAME}"

echo "========================================="
echo "Submitting Training Job"
echo "========================================="
echo "  Model: $MODEL_NAME"
echo "  Datasets: ${DATASET_PATHS[*]}"
echo "  Output Dir: $OUTPUT_DIR"
echo "  Log Dir: $LOG_DIR"
echo "  Use PEFT (LoRA): $USE_PEFT"
echo "========================================="

# Build dataset_paths argument string for heredoc (each path separately quoted)
DATASET_ARGS=""
for path in "${DATASET_PATHS[@]}"; do
    DATASET_ARGS="$DATASET_ARGS \"$path\""
done

# Submit with sbatch
sbatch <<EOF
#!/bin/bash
#SBATCH --job-name=${JOB_NAME}
#SBATCH --output=${LOG_DIR}/%j_${JOB_NAME}.out
#SBATCH --error=${LOG_DIR}/%j_${JOB_NAME}.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=${CPUS}
#SBATCH --gres=${GPUS}
#SBATCH --mem=${MEM}
#SBATCH --time=${TIME}
#SBATCH --partition=${PARTITION}
#SBATCH --account=${ACCOUNT}

# Environment Setup
export CUDA_HOME=/sw/rl9g/cuda/12.4.1/rl9_binary
source "${PROJECT_ROOT}/../../.env"

export HF_DATASETS_CACHE=~/.cache
export HF_CACHE_DIR=~/.cache
export HF_HOME=~/.cache/huggingface
export HF_HUB_CACHE=~/.cache/huggingface/hub
export HF_TOKEN=your-hf-token-here
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True


# WandB Configuration
# export WANDB_PROJECT="multiuser-llm-training"

echo "Date: \$(date)"
echo "Node: \$(hostname)"
echo "WorkDir: ${PROJECT_ROOT}"

# Navigate to script directory to ensure imports work if needed
cd "${PROJECT_ROOT}/training"

echo "Launching training..."

# Run Python Script with Arguments
accelerate launch --num_processes=2 --deepspeed_config_file="${DEEPSPEED_CONFIG}" "${TRAIN_SCRIPT}" \\
    --model_name_or_path "${MODEL_NAME}" \\
    --dataset_paths ${DATASET_ARGS} \\
    --new_model_name "${NEW_MODEL_NAME}" \\
    --output_dir "${OUTPUT_DIR}" \\
    --num_train_epochs ${NUM_EPOCHS} \\
    --per_device_train_batch_size ${BATCH_SIZE} \\
    --gradient_accumulation_steps ${GRAD_ACCUM} \\
    --learning_rate ${LEARNING_RATE} \\
    --use_peft ${USE_PEFT} \\
    --max_length 16384

echo "Job finished."
EOF

echo "Job submitted for ${NEW_MODEL_NAME}"
