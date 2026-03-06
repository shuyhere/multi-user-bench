import argparse
import os
import random
import json
import sys

# Import from sibling
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from generate_meeting_scenarios import generate_scenario_complex

def main():
    parser = argparse.ArgumentParser(description="Generate controlled variable experiments for meeting scheduling")
    parser.add_argument("--count_per_setting", type=int, default=10, help="Number of scenarios per difficulty per user count")
    parser.add_argument("--min_users", type=int, default=2)
    parser.add_argument("--max_users", type=int, default=5)
    parser.add_argument("--output_dir", type=str, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    random.seed(args.seed)
    
    modes = ["full", "partial"]
    difficulties = ["consensus", "negotiation", "partial"]
    
    # Calculate how many scenarios we will generate
    # structure: [mode] -> list of scenarios
    data = {m: [] for m in modes}
    
    scenario_global_counter = 0
    total_base_scenarios = (args.max_users - args.min_users + 1) * len(difficulties) * args.count_per_setting
    
    print(f"Generating controlled meeting scenarios...")
    print(f"User range: {args.min_users} to {args.max_users}")
    print(f"Count per setting: {args.count_per_setting}")
    print(f"Total base scenarios: {total_base_scenarios}")
    print(f"Modes: {modes}")
    
    for n_users in range(args.min_users, args.max_users + 1):
        print(f"  Processing {n_users} users...")
        for diff in difficulties:
            for i in range(args.count_per_setting):
                scenario_global_counter += 1
                # Use a specific seed for this scenario instance to different modes are identical prefixes
                base_seed = args.seed + scenario_global_counter
                
                # Generate for each mode with SAME seed
                for mode in modes:
                    random.seed(base_seed) # RESET SEED TO ENSURE IDENTICAL BASE GENERATION
                    
                    scen = generate_scenario_complex(
                        num_users=n_users,
                        scenario_id_base=scenario_global_counter,
                        difficulty=diff,
                        disclosure_mode=mode
                    )
                    
                    # Distinguish ID by mode
                    scen['id'] = f"{scen['id']}_{mode}"
                    
                    data[mode].append(scen)
                    
    # Save files
    print("\nSaving files...")
    for mode in modes:
        filename = f"disclosure_{mode}_{args.min_users}_to_{args.max_users}_each_{args.count_per_setting}.jsonl"
        filepath = os.path.join(args.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            for item in data[mode]:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"  Saved {len(data[mode])} scenarios to {filepath}")

if __name__ == "__main__":
    main()
