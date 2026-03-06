
import sys
import os
import argparse
import json
import concurrent.futures
from tqdm import tqdm

# Unbuffered output for debugging
sys.stdout.reconfigure(line_buffering=True)
print("Initializing script...", flush=True)

# Add parent directory to path to allow importing from data_generation
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Imports complete. Loading api_client...", flush=True)
from api_client import call_model
print("api_client loaded.", flush=True)

from configs.config import SCENARIO_CATEGORIES, TEACHER_MODEL, NUM_SCENARIOS_PER_CATEGORY

GENERATION_PROMPT_TEMPLATE = """
Generate a single distinct multi-user conversation scenario for the category: "{category}".

The scenario must follow this JSON structure:
{{
    "id": "category_unique_id",
    "category": "{category}",
    "title": "Short Descriptive Title",
    "num_users": Integer (2-10),
    "participants": [
        {{
            "id": "UserIDs (First names)",
            "role": "Job Title or Role",
            "background": "Brief personality and context. Important: If the user is disruptive, include a 'behavior_cue' field with private instructions.",
            "behavior_cue": "Optional private instruction for disruptive behavior (only for 1 in 10 users)"
        }}
    ],
    "scenario_description": "2-3 sentences describing the situation, conflict, or goal.",
    "expected_turns": Integer (5-15),
    "complexity": "low/medium/high",
    "has_conflicts": boolean,
    "requires_private_messages": boolean
}}

Requirements:
1. meaningful and diverse roles.
2. Mix of cooperative and conflicting scenarios.
3. specific, realistic backgrounds.
4. If conflict exists, make it substantial (resource allocation, blame, deadlines).
5. Output purely a JSON object. No markdown formatting.
"""

def generate_single_scenario_wrapper(args):
    """Wrapper function for parallel execution"""
    category, prompt, model, max_tokens = args
    try:
        response = call_model(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0, 
            max_tokens=max_tokens
        )
        
        # Clean up response
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        scenario = json.loads(response.strip())
        
        # Handle potential list wrapper
        if isinstance(scenario, list):
            scenario = scenario[0]
        
        return scenario
    except Exception as e:
        return None

def generate_seeds_for_category(category, count=20, max_workers=10):
    generated_scenarios = []
    seen_titles = set()
    
    print(f"Sampling {count} scenarios for {category} in parallel (threads={max_workers})...")
    
    prompt = GENERATION_PROMPT_TEMPLATE.format(category=category)
    
    # Create arguments for each task
    # We pass all necessary data to strictly avoid any closure/global issues in threads, although threads share memory.
    tasks = [(category, prompt, TEACHER_MODEL, 8192) for _ in range(count)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Use tqdm to show progress
        futures = [executor.submit(generate_single_scenario_wrapper, task) for task in tasks]
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=count, desc=f"  Generating {category}", leave=False):
            scenario = future.result()
            if scenario:
                title = scenario.get('title', '').strip()
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    scenario['id'] = f"{category}_{len(generated_scenarios) + 1:03d}"
                    generated_scenarios.append(scenario)

    print(f"  > Generated {len(generated_scenarios)} unique scenarios for {category}.")
    return generated_scenarios

def main():
    parser = argparse.ArgumentParser(description="Generate seed scenarios.")
    parser.add_argument("--count", type=int, default=NUM_SCENARIOS_PER_CATEGORY, help="Number of scenarios per category.")
    parser.add_argument("--max_workers", type=int, default=10, help="Number of parallel threads.")
    args = parser.parse_args()

    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/seeds")
    os.makedirs(output_dir, exist_ok=True)
    
    total_generated = 0
    
    # Ensure count is not None
    count = args.count if args.count else 100
    
    for category in tqdm(SCENARIO_CATEGORIES, desc="Categories"):
        scenarios = generate_seeds_for_category(category, count=count, max_workers=args.max_workers)
        
        for s in scenarios:
            # Ensure ID is unique
            safe_title = "".join(x for x in s['title'] if x.isalnum())
            filename = f"{category}_{safe_title}.json"
            path = os.path.join(output_dir, filename)
            
            with open(path, 'w') as f:
                json.dump(s, f, indent=2)
            
            total_generated += 1

    print(f"\nDone! Generated {total_generated} new seed scenarios in {output_dir}")

if __name__ == "__main__":
    main()
