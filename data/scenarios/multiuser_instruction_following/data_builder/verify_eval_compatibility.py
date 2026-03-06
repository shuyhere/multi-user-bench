import json
import os
import sys

# Ensure IHEval is in path
sys.path.append(os.path.abspath("IHEval/src"))
sys.path.append(os.path.abspath("IHEval/src/rule_following/evaluate"))

try:
    from rule_following.evaluate import instructions_registry
    from rule_following.evaluate import instructions_util
except ImportError as e:
    print(f"Error importing IHEval: {e}")
    sys.exit(1)

def verify_compatibility(filepath):
    print(f"Checking compatibility for {filepath}...")
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    issues = 0
    total_instructions = 0
    valid_instructions = 0
    
    with open(filepath, 'r') as f:
        for line_idx, line in enumerate(f):
            try:
                entry = json.loads(line)
                gt = entry.get("iheval_ground_truth", {})
                inst_ids = gt.get("instruction_id_list", [])
                kwargs_list = gt.get("kwargs", [])
                
                if len(inst_ids) != len(kwargs_list):
                    print(f"[Line {line_idx}] Mismatch: {len(inst_ids)} IDs vs {len(kwargs_list)} kwargs")
                    issues += 1
                    continue
                
                for i, inst_id in enumerate(inst_ids):
                    total_instructions += 1
                    kw = kwargs_list[i]
                    
                    # 1. Check if ID exists in registry
                    if inst_id not in instructions_registry.INSTRUCTION_DICT:
                        print(f"[Line {line_idx}] Unknown Instruction ID: {inst_id}")
                        issues += 1
                        continue
                        
                    # 2. Try to instantiate and build description
                    try:
                        instruction_cls = instructions_registry.INSTRUCTION_DICT[inst_id]
                        instruction = instruction_cls(inst_id)
                        
                        # Fix for prompt_to_repeat which might depend on exact kwargs
                        # Some instructions might require 'prompt' in build_description if it was part of the original logic
                        # But typically kwargs from IHEval 'answer' field are sufficient for build_description
                        
                        instruction.build_description(**kw)
                        valid_instructions += 1
                        
                    except Exception as e:
                        print(f"[Line {line_idx}] Failed to build {inst_id} with kwargs {kw}: {e}")
                        issues += 1
                        
            except json.JSONDecodeError:
                print(f"[Line {line_idx}] Invalid JSON")
                issues += 1
                
    print(f"Checked {total_instructions} instructions.")
    print(f"Valid: {valid_instructions}")
    print(f"Issues: {issues}")
    if issues == 0:
        print("PASS: All instructions are compatible with IHEval validators.")
    else:
        print("FAIL: Found compatibility issues.")
    print("-" * 40)

def main():
    base_dir = "data/scenarios/multiuser_instruction_following/data_builder/controlled_exp"
    files = [
        "aligned_2_to_10.jsonl",
        "conflict_2_to_10.jsonl"
    ]
    
    for fname in files:
        verify_compatibility(os.path.join(base_dir, fname))

if __name__ == "__main__":
    main()
