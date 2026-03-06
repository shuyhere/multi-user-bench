#!/usr/bin/env bash
set -euo pipefail

# ============================
# 改进的训练配置 - 方案 1（推荐）
# 仅使用 multi-user 数据 + LoRA 训练
# ============================

# Model and Dataset
MODEL_NAME="Qwen/Qwen3-4B-Instruct-2507"

# 关键改变：仅使用 multi-user 数据
DATASET_PATHS=(
    "<PATH_TO_TRAINING_DATA>/multi_user_training.jsonl"
)

NEW_MODEL_NAME="qwen3-4b-it-2507-multiuser-lora-v2-clean"

# 训练超参数 - 优化配置
NUM_EPOCHS=2  # 减少到 2 epochs 避免过拟合
BATCH_SIZE=2  # 增加 batch size
GRAD_ACCUM=2  # 减少梯度累积
LEARNING_RATE=5e-6  # 降低学习率（从 2e-5 降到 5e-6）
USE_PEFT=true  # 启用 LoRA 避免灾难性遗忘
MAX_GRAD_NORM=1.0  # 添加梯度裁剪

# Resources
GPUS="gpu:a100:2"
MEM="256G"
CPUS=10
TIME="12:00:00"  # 减少时间（2 epochs 应该足够）
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
echo "提交改进的训练任务"
echo "========================================="
echo "  模型: $MODEL_NAME"
echo "  数据集: ${DATASET_PATHS[*]}"
echo "  输出目录: $OUTPUT_DIR"
echo "  日志目录: $LOG_DIR"
echo "  使用 PEFT (LoRA): $USE_PEFT"
echo "  学习率: $LEARNING_RATE"
echo "  Epochs: $NUM_EPOCHS"
echo "  Batch Size: $BATCH_SIZE"
echo "  梯度累积: $GRAD_ACCUM"
echo "========================================="

# Build dataset_paths argument string for heredoc
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
export WANDB_PROJECT="multiuser-llm-training-v2"

echo "Date: \$(date)"
echo "Node: \$(hostname)"
echo "WorkDir: ${PROJECT_ROOT}"

# Navigate to script directory
cd "${PROJECT_ROOT}/training"

echo "启动改进的训练..."

# Run Python Script with Arguments
/ibex/project/c2328/Muses-bench/.venv/bin/accelerate launch --num_processes=2 --deepspeed_config_file="${DEEPSPEED_CONFIG}" "${TRAIN_SCRIPT}" \\
    --model_name_or_path "${MODEL_NAME}" \\
    --dataset_paths ${DATASET_ARGS} \\
    --new_model_name "${NEW_MODEL_NAME}" \\
    --output_dir "${OUTPUT_DIR}" \\
    --num_train_epochs ${NUM_EPOCHS} \\
    --per_device_train_batch_size ${BATCH_SIZE} \\
    --gradient_accumulation_steps ${GRAD_ACCUM} \\
    --learning_rate ${LEARNING_RATE} \\
    --use_peft ${USE_PEFT} \\
    --max_length 8192 \\
    --max_grad_norm ${MAX_GRAD_NORM} \\
    --warmup_ratio 0.1 \\
    --lr_scheduler_type cosine \\
    --logging_steps 10 \\
    --save_strategy epoch \\
    --evaluation_strategy no

echo "训练完成！"
EOF

echo "任务已提交: ${NEW_MODEL_NAME}"
echo ""
echo "监控训练进度："
echo "  tail -f ${LOG_DIR}/*_${JOB_NAME}.out"
echo ""
echo "关注指标："
echo "  - loss 应该稳定下降（目标 < 1.0）"
echo "  - grad_norm 应该 < 2.0"
echo "  - mean_token_accuracy 应该 > 0.75"
