
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

import torch
import transformers
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    set_seed,
    AutoConfig,
)
from trl import (
    ModelConfig,
    SFTConfig,
    SFTTrainer,
    TrlParser,
    get_peft_config,
    get_quantization_config,
    get_quantization_config,
    get_kbit_device_map
)
from transformers import DataCollatorForLanguageModeling
import numpy as np

# Set up logging
logger = logging.getLogger(__name__)

@dataclass
class ScriptArguments:
    dataset_paths: list[str] = field(
        default_factory=lambda: ["multiuser_llm_training/data_generation/data/training/multi_user_training.jsonl","multiuser_llm_training/data_generation/data/training/capybara_train.jsonl"],
        metadata={"help": "List of paths to local dataset files (jsonl)."}
    )
    new_model_name: str = field(
        default="qwen3-4b-multiuser-lora_mix",
        metadata={"help": "Name for the saved model."}
    )
    dataset_name: Optional[str] = field(
        default=None, metadata={"help": "Dataset name (HuggingFace Hub)"}
    )
    dataset_config: Optional[str] = field(
        default=None, metadata={"help": "Dataset config"}
    )
    dataset_streaming: bool = field(
        default=False, metadata={"help": "Stream dataset"}
    )
    dataset_train_split: str = field(
        default="train", metadata={"help": "Train split"}
    )
    dataset_test_split: str = field(
        default="test", metadata={"help": "Test split"}
    )


class DataCollatorForCompletionOnlyLM(DataCollatorForLanguageModeling):
    def __init__(self, response_template, tokenizer, mlm=False):
        super().__init__(tokenizer=tokenizer, mlm=mlm)
        self.response_template = response_template
        self.response_token_ids = self.tokenizer.encode(self.response_template, add_special_tokens=False)
    
    def torch_call(self, examples):
        batch = super().torch_call(examples)
        labels = batch["labels"].clone()
        
        for i in range(len(labels)):
            # Set everything to -100 (ignore) initially
            new_labels = torch.full_like(labels[i], -100)
            
            # Find response_template occurrences
            seq = labels[i].tolist()
            n = len(self.response_token_ids)
            matches = []
            for j in range(len(seq) - n + 1):
                if seq[j:j+n] == self.response_token_ids:
                    matches.append(j)
            
            # Identify next turn start marker (<|im_start|>)
            im_start_tokens = self.tokenizer.encode("<|im_start|>", add_special_tokens=False)
            
            for start_idx in matches:
                content_start = start_idx + n
                end_idx = len(seq)
                
                # Find start of next turn to stop unmasking
                for k in range(content_start, len(seq) - len(im_start_tokens) + 1):
                    if seq[k:k+len(im_start_tokens)] == im_start_tokens:
                        end_idx = k
                        break
                
                # Restore original labels for the assistant response
                new_labels[content_start:end_idx] = labels[i][content_start:end_idx]
                
            batch["labels"][i] = new_labels

        return batch

def main():
    parser = TrlParser((ScriptArguments, SFTConfig, ModelConfig))
    
    # Define our preferred defaults here
    default_script_args = ScriptArguments()
    default_model_args = ModelConfig(
        model_name_or_path="Qwen/Qwen3-4B-Base",
        attn_implementation="flash_attention_2",
        lora_r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        lora_target_modules=["all-linear"],
        use_peft=True,  # Default to LoRA
        load_in_4bit=False,  # Will be set to True only if use_peft=True
        dtype="bfloat16" 
    )
    default_training_args = SFTConfig(
        output_dir="./results",
        num_train_epochs=3,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        gradient_checkpointing=True,
        assistant_only_loss=True,
        logging_steps=10,
        learning_rate=2e-5,
        fp16=False,
        bf16=True,
        max_grad_norm=0.3,
        warmup_ratio=0.1,
        lr_scheduler_type="constant",
        report_to="trackio",
        push_to_hub=False,
        max_length=32768,
        packing=False,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=5,
        dataset_kwargs={"add_special_tokens": False, "append_concat_token": False}
    )

    if len(sys.argv) == 1:
        # No CLI arguments, use our hardcoded defaults
        script_args = default_script_args
        model_args = default_model_args
        training_args = default_training_args
    else:
        # CLI arguments provided. We want to merge them with our script defaults.
        # TrlParser will parse CLI but also use library defaults for missing values.
        # We need to manually override those library defaults with our script defaults.
        cli_script_args, cli_training_args, cli_model_args = parser.parse_args_and_config()
        
        # Merge logic: if an argument was NOT explicitly passed via CLI, use script default.
        # We can check sys.argv for explicit presence of keys, but easier is to check against parser defaults.
        
        def merge_args(cli_args, script_defaults):
            for key, value in script_defaults.__dict__.items():
                # If the CLI arg is the library default but the script default is different, 
                # we only override if the user didn't explicitly pass the library default value.
                # Simplest robust way for users: Script defaults are the "new" defaults.
                # So we override anything that wasn't explicitly changed via CLI.
                
                cli_val = getattr(cli_args, key)
                # Check if it was passed via command line
                arg_name = f"--{key}"
                is_explicit = any(arg.startswith(arg_name) for arg in sys.argv)
                
                if not is_explicit:
                    setattr(cli_args, key, value)
            return cli_args

        script_args = merge_args(cli_script_args, default_script_args)
        model_args = merge_args(cli_model_args, default_model_args)
        training_args = merge_args(cli_training_args, default_training_args)
    
    # Critical: Ensure quantization is only used with PEFT
    # Full fine-tuning cannot use quantized models
    if model_args.use_peft:
        # Enable quantization for LoRA/PEFT training (QLoRA)
        if not any(arg.startswith("--load_in_4bit") for arg in sys.argv):
            model_args.load_in_4bit = True
            logger.info("PEFT enabled: Automatically enabling 4-bit quantization (QLoRA)")
    else:
        # Disable quantization for full fine-tuning
        model_args.load_in_4bit = False
        model_args.load_in_8bit = False
        logger.info("Full fine-tuning mode: Quantization disabled")
        
    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # 1. Model Init Keywords
    model_kwargs = dict(
        revision=model_args.model_revision,
        trust_remote_code=model_args.trust_remote_code,
        attn_implementation=model_args.attn_implementation,
        dtype=torch.float16 if model_args.dtype == "float16" else (torch.bfloat16 if model_args.dtype == "bfloat16" else model_args.dtype),
    )
    
    # Quantization using TRL helper
    quantization_config = get_quantization_config(model_args)
    if quantization_config is not None:
        model_kwargs["device_map"] = get_kbit_device_map()
        model_kwargs["quantization_config"] = quantization_config

    # 2. Load Model
    # Can use AutoModel directly as script does
    model = AutoModelForCausalLM.from_pretrained(
        model_args.model_name_or_path,
        **model_kwargs
    )

    # 3. Load Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_args.model_name_or_path,
        trust_remote_code=model_args.trust_remote_code,
    )
    # Force set chat template to ensure it handles custom roles
    print("Forcing default chat template for custom roles...")
    tokenizer.chat_template = "{% for message in messages %}{% if message['role'] == 'assistant' %}{% generation %}{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>' + '\n'}}{% endgeneration %}{% else %}{{'<|im_start|>' + message['role'] + '\n' + message['content'] + '<|im_end|>' + '\n'}}{% endif %}{% endfor %}{% if add_generation_prompt %}{{ '<|im_start|>assistant\n' }}{% endif %}"
    
    # Ensure special tokens exist if we use them
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 4. Load Dataset
    try:
        # Load all datasets
        from datasets import Dataset, concatenate_datasets
        
        loaded_datasets = []
        paths = script_args.dataset_paths
        
        # 1. Load each dataset
        for path in paths:
            if os.path.exists(path):
                print(f"Loading dataset from {path}")
                try:
                    ds = load_dataset("json", data_files=path, split="train")
                    # Sanitize: ensure it has 'messages' column and remove implementation details like 'reasoning_content'
                    if "messages" not in ds.column_names:
                        logger.warning(f"Dataset {path} has no 'messages' column. Skipping.")
                        continue
                        
                    # Standardize features by rebuilding
                    # This ensures we don't have schema mismatches (e.g. one has 'reasoning_content' inside message dicts and other doesn't)
                    # We strictly copy only role/content
                    print(f"  Sanitizing {path}...")
                    new_data = []
                    for example in ds:
                        new_msgs = []
                        valid_example = True
                        for m in example["messages"]:
                            if "role" not in m or "content" not in m:
                                valid_example = False
                                break
                            new_msgs.append({"role": m["role"], "content": m["content"]})
                        if valid_example:
                            new_data.append({"messages": new_msgs})
                    
                    ds_clean = Dataset.from_list(new_data)
                    loaded_datasets.append(ds_clean)
                    print(f"  Loaded {len(ds_clean)} samples.")
                    
                except Exception as e:
                    logger.error(f"Error loading {path}: {e}")
            else:
                 logger.warning(f"Dataset path {path} not found.")

        if not loaded_datasets:
            if script_args.dataset_name:
                 print(f"Loading from Hub: {script_args.dataset_name}")
                 dataset = load_dataset(script_args.dataset_name, split=script_args.dataset_train_split)
                 loaded_datasets.append(dataset)
            else:
                 raise ValueError("No valid datasets provided.")

        # 2. Balance Datasets (Truncate all to the size of the smallest one)
        if len(loaded_datasets) > 1:
            print("Balancing multiple datasets...")
            min_len = min(len(ds) for ds in loaded_datasets)
            print(f"Minimum dataset size found: {min_len}. Truncating all datasets to this size.")
            
            balanced_datasets = []
            for ds in loaded_datasets:
                balanced_ds = ds.shuffle(seed=42).select(range(min_len))
                balanced_datasets.append(balanced_ds)
            loaded_datasets = balanced_datasets
        
        # 3. Concatenate
        if len(loaded_datasets) > 0:
            # Align features first (cast to the first dataset's features to avoid Arrow schema errors)
            target_features = loaded_datasets[0].features
            final_datasets = []
            for ds in loaded_datasets:
                try:
                    ds_casted = ds.cast(target_features)
                    final_datasets.append(ds_casted)
                except Exception as e:
                    print(f"Warning: Casting features failed: {e}. Trying to concat anyway.")
                    final_datasets.append(ds)
            
            print(f"Concatenating {len(final_datasets)} datasets...")
            dataset = concatenate_datasets(final_datasets)
            dataset = dataset.shuffle(seed=42)
            print(f"Final combined dataset size: {len(dataset)}")
        else:
             raise ValueError("Dataset list is empty after processing.")

    except Exception as e:
        logger.error(f"Dataset load error: {e}")
        # Dummy
        dummy = [{"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]}] * 10
        from datasets import Dataset
        dataset = Dataset.from_list(dummy)
    
    # Debug: Print raw dataset sample
    # Debug: Print raw dataset samples
    print("\n" + "="*50)
    print("[DEBUG] Raw Dataset Samples (First 5):")
    try:
        for i in range(min(5, len(dataset))):
            print(f"Sample {i}:")
            print(dataset[i])
            print("-" * 20)
    except Exception as e:
        print(f"Could not print samples: {e}")
    print("="*50 + "\n")

    # 5. Trainer
    response_template = "<|im_start|>assistant\n"
    collator = DataCollatorForCompletionOnlyLM(response_template=response_template, tokenizer=tokenizer)

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        peft_config=get_peft_config(model_args) if model_args.use_peft else None,
        processing_class=tokenizer,
        # data_collator handled by SFTTrainer when assistant_only_loss=True
    )

    logger.info("Starting training...")
    trainer.train()
    
    logger.info(f"Saving to {training_args.output_dir}")
    trainer.save_model(training_args.output_dir)

if __name__ == "__main__":
    main()
