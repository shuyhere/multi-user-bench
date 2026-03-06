
import os
import glob
import json
from tqdm import tqdm
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from format_converter import FormatConverter

def aggregate_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    generated_dir = os.path.join(base_dir, "data/generated")
    output_path = os.path.join(base_dir, "data/training/multi_user_training.jsonl")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Find all raw JSONL files
    raw_files = glob.glob(os.path.join(generated_dir, "raw_*.jsonl"))
    
    if not raw_files:
        print(f"No generated files found in {generated_dir}")
        return

    print(f"Found {len(raw_files)} raw data files.")
    
    all_conversations = []
    
    # Aggregate
    for fpath in tqdm(raw_files, desc="Aggregating files"):
        try:
            with open(fpath, 'r') as f:
                for line in f:
                    if line.strip():
                        all_conversations.append(json.loads(line))
        except Exception as e:
            print(f"Error reading {fpath}: {e}")
            
    print(f"Total conversations collected: {len(all_conversations)}")
    
    # Convert to training format
    converter = FormatConverter()
    converter.batch_convert(all_conversations, output_path)
    
    print(f"Final training dataset saved to: {output_path}")
    
    # Statistics
    total_turns = sum(c['total_agent_turns'] for c in all_conversations)
    print(f"Total Agent Turns: {total_turns}")

if __name__ == "__main__":
    aggregate_data()
