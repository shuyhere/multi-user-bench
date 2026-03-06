import os
import json
from pathlib import Path
from typing import List, Dict, Set, Tuple

def setup_output_structure(task_name: str, model: str, data_file: str, max_turns: int, debug: bool, output_file: str = None):
    """
    Setup standardized output directory structure.
    Format: results/{task}_{safe_model}_{data_stem}_{max_turns}{_debug}/
    Inside: detail.jsonl, eva.json
    """
    # If output_file is provided, use it directly (assume caller handles naming)
    if output_file:
        output_path = Path(output_file)
        # Create parent directory
        os.makedirs(output_path.parent, exist_ok=True)
        
        log_file = output_path
        # Derive eva.json path from log_file by replacing extension/suffix
        # e.g. results.jsonl -> eva.json
        if log_file.name == "detail.jsonl":
            eva_file = log_file.parent / "eva.json"
        else:
             eva_file = log_file.parent / "eva.json" # Force standard name in same dir
             # Or: eva_file = log_file.with_name("eva.json")
             
        print(f"[INFO] Using provided output file: {log_file}")
        print(f"[INFO] Evaluation Summary will be saved to: {eva_file}")
        return log_file, eva_file

    # Auto-generate folder name
    
    data_stem = Path(data_file).stem if data_file else "unknown_data"
    safe_model = model.replace("/", "-")
    
    if debug:
        safe_model += "_debug"
    
    # Hierarchical structure: results/{task}/{dataset}/{model}
    output_dir = Path("results") / task_name / data_stem / safe_model
    
    os.makedirs(output_dir, exist_ok=True)
    
    log_file = output_dir / "detail.jsonl"
    eva_file = output_dir / "eva.json"
    
    print(f"[INFO] Output Directory: {output_dir}")
    print(f"[INFO] Detailed Log: {log_file}")
    print(f"[INFO] Evaluation: {eva_file}")
    
    return log_file, eva_file


def load_existing_results(log_file: str, required_keys: List[str] = None) -> Tuple[List[Dict], Set[str]]:
    """Load existing results from a JSONL log file for resume capability."""
    results = []
    processed_ids = set()
    
    if os.path.exists(log_file):
        print(f"Found existing log file: {log_file}. Resuming...")
        try:
            with open(log_file, 'r', encoding='utf-8') as f_in:
                for line in f_in:
                    if line.strip():
                        try:
                            res = json.loads(line)
                            
                            # Validation: check for required keys (e.g. for schema updates)
                            if required_keys:
                                missing = [k for k in required_keys if k not in res]
                                if missing:
                                    print(f"[RESUME SKIP] Ignoring old result for {res.get('scenario_id')}: missing keys {missing}")
                                    continue
                                    
                            results.append(res)
                            scenario_id = res.get("scenario_id")
                            if scenario_id:
                                processed_ids.add(scenario_id)
                        except json.JSONDecodeError:
                            print(f"Skipping malformed line in {log_file}")
            print(f"Loaded {len(results)} valid existing results.")
        except Exception as e:
             print(f"Error reading existing log file: {e}")
             
    return results, processed_ids
