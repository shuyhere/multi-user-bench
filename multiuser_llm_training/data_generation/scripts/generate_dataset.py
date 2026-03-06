import sys
import os
# Unbuffered output
sys.stdout.reconfigure(line_buffering=True)
print("Starting generate_dataset.py...", flush=True)

# Add parent directory to path to allow importing modules from data_generation root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import glob
import concurrent.futures
from threading import Lock
import random
import argparse
from tqdm import tqdm

print("Imports complete.", flush=True)

from configs.config import *
from seed_scenarios import SEED_SCENARIOS
from conversation_generator import ConversationGenerator
from format_converter import FormatConverter

def load_seeds_from_dir(directory):
    """Load all JSON seed scenarios from directory"""
    print(f"Loading seeds from {directory}...", flush=True)
    seeds = []
    files = glob.glob(os.path.join(directory, "*.json"))
    for f in files:
        try:
            with open(f, 'r') as fd:
                data = json.load(fd)
                # Store filename base for consistent output naming
                data['_safe_id'] = os.path.basename(f).replace('.json', '')
                seeds.append(data)
        except Exception as e:
            print(f"Error loading seed {f}: {e}")
    return seeds

def process_single_scenario(args):
    """Worker function to generate conversations for a single scenario"""
    detailed = False
    output_path = None
    
    if len(args) == 6:
        scenario, generator_instance, pbar, detailed, output_path, conversations_per_seed = args
    elif len(args) == 5:
        scenario, generator_instance, pbar, detailed, output_path = args
        conversations_per_seed = 20
    elif len(args) == 4:
        scenario, generator_instance, pbar, detailed = args
        conversations_per_seed = 20
    else:
        scenario, generator_instance, pbar = args
        conversations_per_seed = 20
        
    # Determine output path if not provided
    if not output_path:
        # Use safe id from load or scenario id
        safe_name = scenario.get('_safe_id', scenario['id'])
        output_path = f"data/generated/raw_{safe_name}.jsonl"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    generated_docs = []
    
    # Check for existing progress (Resume capability)
    items_to_skip = 0
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r') as f:
                items_to_skip = sum(1 for line in f if line.strip())
            if detailed:
                print(f"Resuming: found {items_to_skip} existing conversations in {output_path}")
        except Exception as e:
            print(f"Error reading existing file {output_path}: {e}")

    # Total conversations per seed

    
    if items_to_skip >= conversations_per_seed:
        if detailed:
            print(f"Skipping {scenario['id']}: Already has {items_to_skip} conversations.")
        if pbar:
            pbar.update(conversations_per_seed if not detailed else 0)
        return []
    
    # Update pbar for skipped items if using detailed view 
    # (If using simple view, we update once at end, so don't update here)
    if detailed and pbar and items_to_skip > 0:
        pbar.update(items_to_skip)
    
    for turn_type, ratio in TURN_DISTRIBUTION.items():
        # Calculate number based on ratio, minimum 1 if ratio > 0
        count = max(1, int(conversations_per_seed * ratio)) if ratio > 0 else 0
        
        if count == 0:
            continue
        
        if turn_type == "single_turn":
            target_turns = 2
        elif turn_type == "short":
            target_turns = random.randint(2, 5)
        elif turn_type == "medium":
            target_turns = random.randint(6, 10)
        else:
            target_turns = random.randint(11, MAX_TURNS)
            
        for _ in range(count):
            # Resume logic: skip already generated items
            if items_to_skip > 0:
                items_to_skip -= 1
                continue
                
            try:
                # Select a random teacher model for this conversation
                selected_model = random.choice(CANDIDATE_MODELS)
                
                # if detailed:
                #     print(f"Generating {scenario['id']} conv {_+1}/{count} with {selected_model}...", flush=True)

                if turn_type == "single_turn":
                    conv = generator_instance.generate_single_turn_conversation(scenario, model_name=selected_model)
                else:
                    conv = generator_instance.generate_conversation(scenario, target_turns, model_name=selected_model)
                generated_docs.append(conv)
                
                # INCREMENTAL SAVE
                with open(output_path, 'a') as f:
                    f.write(json.dumps(conv, ensure_ascii=False) + '\n')
                
                # Update detailed pbar if requested
                if detailed and pbar:
                    pbar.update(1)
                    
            except Exception as e:
                # Log error
                print(f"Error generating {scenario['id']}: {e}", flush=True)
                import traceback
                traceback.print_exc()
                
    if pbar and not detailed:
        pbar.update(1)
        
    return generated_docs

import argparse

def main():
    """Generate complete training dataset"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed_file", type=str, help="Path to specific seed file to process")
    parser.add_argument("--count", type=int, default=100, help="Number of conversations per seed")
    parser.add_argument("--max_workers", type=int, default=MAX_WORKERS, help="Number of parallel worker threads")
    args = parser.parse_args()
    
    print("=" * 60)
    print("Multi-User Conversation Dataset Generation")
    print("=" * 60)
    
    print(f"Arguments: {args}")
    
    seeds = []
    
    if args.seed_file:
        print(f"Processing single seed file: {args.seed_file}")
        if not os.path.exists(args.seed_file):
            print(f"ERROR: Seed file not found: {args.seed_file}")
            return

        try:
            with open(args.seed_file, 'r') as f:
                data = json.load(f)
                data['_safe_id'] = os.path.basename(args.seed_file).replace('.json', '')
                seeds.append(data)
        except Exception as e:
            print(f"Error loading seed file: {e}")
            return
    else:
        # Load from directory
        print(f"Using Max Workers: {args.max_workers}")
        seeds_dir = os.path.join(os.path.dirname(__file__), "../data/seeds")
        seeds = load_seeds_from_dir(seeds_dir)
        print(f"Loaded {len(seeds)} seed scenarios from {seeds_dir}")
    
    if not seeds:
        print("No seeds found!")
        return
    
    print(f"Seeds loaded: {len(seeds)}")
    if seeds:
        print(f"Seed content example (ID): {seeds[0].get('id', 'Unknown')}")

    # 2. Setup Generator
    print("Initializing Generator...", flush=True)
    generator = ConversationGenerator()
    converter = FormatConverter()
    print("Generator initialized.", flush=True)
    
    # 3. Execution
    if args.seed_file:
        # Sequential processing for single file
        print(f"Generating conversations for single seed...", flush=True)
        
        # Calculate output path
        basename = os.path.basename(args.seed_file).replace('.json', '')
        output_path = f"data/generated/raw_{basename}.jsonl"
        
        # Use tqdm for detailed progress
        with tqdm(total=args.count, desc="Generating convs") as pbar:
            results = process_single_scenario((seeds[0], generator, pbar, True, output_path, args.count))
        print(f"Generation finished.")
        # We don't need to aggregate here as file is written incrementally
    else:
        # Parallel Execution for all seeds
        print(f"Starting generation with {args.max_workers} threads...")
        with tqdm(total=len(seeds), desc="Scenarios Processed") as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.max_workers) as executor:
                # pass dicts, they have _safe_id to help determine path
                futures = [executor.submit(process_single_scenario, (seed, generator, pbar, False, None, args.count)) for seed in seeds]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result() # Wait for completion, exceptions printed in thread
                    except Exception as e:
                        print(f"Worker failed: {e}")

    print(f"\n\nGeneration complete.")
if __name__ == "__main__":
    main()
