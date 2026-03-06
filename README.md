<h1 align="center"><a href="https://korde-ai.github.io/multi-user-llm/">🎭 Multi-User Large Language Model Agents</a></h1>
<p align="center">
  <a href="https://arxiv.org/abs/XXXX.XXXXX"><img src="https://img.shields.io/badge/arXiv-XXXX.XXXXX-b31b1b.svg" alt="arXiv"></a>
  <a href="https://korde-ai.github.io/multi-user-llm/"><img src="https://img.shields.io/badge/Project-Page-1E3A5F.svg" alt="Project Page"></a>
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://www.python.org/downloads/release/python-3100/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
</p>
<p align="center">
  <img src="assets/affiliations_v2.png" alt="Stanford University · KAUST · University of Toronto · MIT" height="80">
</p>

Official code for the paper: **"Multi-User Large Language Model Agents"**

> LLM-based agents are increasingly capable of navigating complex environments, but prior work overwhelmingly assumes a single user with a single utility function. Real-world deployments involve **multiple users** with different roles, permissions, and preferences. Multi-User LLM provides a formal framework and benchmark to evaluate how LLM agents handle multi-user interactions.

---

## 📋 Overview

Multi-User LLM evaluates four fundamental capabilities of multi-user LLM agents:

| Capability | Scenario | What It Tests |
|:---|:---|:---|
| 🔐 **Privacy & Access Control** | Secure Credential Management | Permission enforcement, privacy-aware summarization, resistance to social engineering |
| 📅 **Sequential Coordination** | Meeting Scheduling | Preference elicitation, conflict resolution, scalable context management |
| ⚡ **Resource Optimization** | Shared LLM Inference Queue | Fairness, queueing efficiency, incentive compatibility |
| 📝 **Instruction Following** | Multi-User Instructions | Following per-user constraints in multi-stakeholder settings |

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/shuyhere/multi-user-llm.git
cd multi-user-llm
pip install -e .
```

### Configuration

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your API credentials:

```bash
# For OpenAI models
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# For Anthropic models
ANTHROPIC_API_KEY=your-api-key-here

# For other providers supported by LiteLLM
# See: https://docs.litellm.ai/docs/providers
```

### Run a Scenario

```bash
python run.py \
    --scenario access_control \
    --data data/scenarios/access_control/test_datasets/controlled_exp_large/template_xml_attack_none_2_to_10_each_2.jsonl \
    --model gpt-4o-mini \
    --provider openai \
    --output results/ac_results.jsonl
```

Supported scenarios: `access_control`, `meeting_scheduling`, `shared_queue`, `multiuser_instruction_following`. See `python run.py --help` for all arguments.

## 📊 Benchmark Datasets

All test data is in `data/scenarios/`. Each scenario provides ready-to-use JSONL files and a **data builder** script for generating custom datasets. See the `data_builder/` directory under each scenario for details.

## 🎓 Training Multi-User LLM Agents

We provide a complete training pipeline for fine-tuning LLMs on multi-user conversations.

### 1. Generate Training Data

```bash
# Generate seed scenarios
python multiuser_llm_training/data_generation/scripts/generate_seeds.py

# Generate full conversations using a teacher model
python multiuser_llm_training/data_generation/scripts/generate_dataset.py

# Aggregate and format data
python multiuser_llm_training/data_generation/scripts/aggregate_data.py
```

### 2. Train

```bash
# Configure training paths in submit_training.sh, then:
sbatch multiuser_llm_training/training/submit_training.sh

# Or run directly
python multiuser_llm_training/training/train.py \
    --model_name_or_path <base-model> \
    --dataset_name <path-to-training-data> \
    --output_dir <output-dir>
```

### 3. Evaluate Trained Model

```bash
# Use vLLM provider with optional LoRA
python run.py \
    --scenario access_control \
    --data data/scenarios/access_control/test_datasets/controlled_exp_large/template_xml_attack_none_2_to_10_each_2.jsonl \
    --model <your-model-path> \
    --provider vllm \
    --lora-path <optional-lora-path> \
    --output results/trained_model_results.jsonl
```

## 📁 Project Structure

```
.
├── run.py                  # Main entry point
├── setup.py                # Package setup
├── .env.example            # API credentials template
├── LICENSE                 # Apache 2.0
│
├── muses_bench/            # Core benchmark package
│   ├── core/               # User, Message, Context types
│   ├── agents/             # LLM agent + simulated users
│   ├── envs/               # Scenario environments
│   ├── evaluators/         # Scenario runners
│   ├── metrics/            # Metric computation
│   ├── tools/              # Tool interfaces
│   └── utils/              # Utilities
│
├── data/                   # Benchmark data
│   └── scenarios/          # Per-scenario JSONL datasets + builders
│
├── multiuser_llm_training/ # Training pipeline
│   ├── data_generation/    # Synthetic data generation
│   └── training/           # SFT training scripts
│
└── scripts/                # Batch evaluation helpers
```

## 📄 License

This project is licensed under the [Apache License 2.0](LICENSE).

## 📝 Citation

TODO

