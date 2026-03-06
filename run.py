"""
Main entry point for running Muses-bench scenarios.

Usage:
    python run.py --scenario shared_queue --model claude-3-5-sonnet-20241022 --provider anthropic
    python run.py --scenario access_control --data data/scenarios/access_control/user_simulate/no_persona_singleturn.jsonl --model gpt-4o-mini
    python run.py --scenario meeting_scheduling --model gpt-4o --provider openai
    
"""

import argparse
import os
from pathlib import Path
import sys

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from .env file in the current directory or parent directories
    # Use override=True to ensure .env values take precedence over system env vars
    dotenv_path = Path(__file__).parent / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path, override=True)
        print(f"[INFO] Loaded .env from: {dotenv_path}")
    else:
        load_dotenv(override=True)  # Try default locations
except ImportError:
    pass  # dotenv not installed, use system env vars

# Import evaluators
from muses_bench.evaluators.meeting_scheduling import run_meeting_scheduling_batch
from muses_bench.evaluators.shared_queue import run_shared_queue
from muses_bench.evaluators.access_control import run_access_control_batch
from muses_bench.evaluators.instruction_following import run_instruction_following_batch


def main():
    parser = argparse.ArgumentParser(description="Run Muses-bench scenarios")
    parser.add_argument(
        "--scenario",
        type=str,
        required=True,
        choices=["meeting_scheduling", "shared_queue", "access_control", "multiuser_instruction_following"],
        help="Scenario to run"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="Model name (e.g., gpt-4o-mini, claude-3-5-sonnet-20241022)"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="openai",
        help="LLM provider (e.g., openai, anthropic, google)"
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=15,
        help="Maximum turns/steps per episode (default: 15)"
    )
    
    parser.add_argument(
        "--data",
        type=str,
        required=True,
        help="Data file for batch scenarios (JSONL format)"
    )
    parser.add_argument(
        "--user-model",
        type=str,
        help="Model for simulated users (defaults to same as --model)"
    )
    parser.add_argument(
        "--lora-path",
        type=str,
        help="Path to LoRA adapter (optional, for vllm provider)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for batch test results"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode: run only first 3 samples, detailed logging"
    )
    parser.add_argument(
        "--use-training-format",
        action="store_true",
        help="Use training-compatible format (@UserName: message style) instead of XML tags"
    )
    
    args = parser.parse_args()
    
    print(f"\nRunning Muses-bench")
    print(f"Scenario: {args.scenario}")
    print(f"Model: {args.model}")
    print(f"Provider: {args.provider}")
    
    llm_client = None
    lora_request = None
    
    if args.provider == "vllm":
        try:
            from muses_bench.utils.vllm_client import load_vllm_model, cleanup_vllm
            print(f"[INFO] Initializing vLLM model: {args.model}")
            llm_client, lora_request = load_vllm_model(args.model, args.lora_path)
            print("[INFO] vLLM model loaded successfully")
        except ImportError:
            print("[ERROR] vLLM requested but not installed or vllm_client missing.")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Failed to load vLLM model: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    try:
        # Run the selected scenario
        if args.scenario == "meeting_scheduling":
            run_meeting_scheduling_batch(
                args.data, args.model, args.provider, args.user_model, args.output, args.max_turns, args.debug,
                llm_client=llm_client, lora_request=lora_request, use_training_format=args.use_training_format
            )
            print(f"\n{'=' * 70}")
            print(f"Run Complete!")
            print(f"{'=' * 70}\n")
        elif args.scenario == "shared_queue":
            run_shared_queue(
                args.data, args.model, args.provider, args.user_model, args.output, args.max_turns, args.debug,
                llm_client=llm_client, lora_request=lora_request, use_training_format=args.use_training_format
            )
            print(f"\n{'=' * 70}")
            print(f"Run Complete!")
            print(f"{'=' * 70}\n")
        elif args.scenario == "access_control":
            run_access_control_batch(
                args.data, 
                args.model, 
                args.provider, 
                args.user_model,
                args.output,
                args.max_turns,
                args.debug,
                llm_client=llm_client,
                lora_request=lora_request,
                use_training_format=args.use_training_format
            )
        elif args.scenario == "multiuser_instruction_following":
            run_instruction_following_batch(
                args.data,
                args.model,
                args.provider,
                args.user_model,
                args.output,
                args.max_turns,
                args.debug,
                llm_client=llm_client,
                lora_request=lora_request,
                use_training_format=args.use_training_format
            )
            
    finally:
        if args.provider == "vllm" and llm_client is not None:
            print("[INFO] Cleaning up vLLM model...")
            cleanup_vllm(llm_client)

if __name__ == "__main__":
    main()
