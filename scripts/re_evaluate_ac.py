import json
import argparse
import os
from tqdm import tqdm
from muses_bench.metrics.access_control_metrics import evaluate_access_control

def load_dataset_map(data_file):
    """Load dataset and create a map from scenario_id to full data."""
    scenario_map = {}
    with open(data_file, 'r') as f:
        for line in f:
            if not line.strip(): continue
            item = json.loads(line)
            scenario_map[item['id']] = item
    return scenario_map

def reconstruct_responses(conversation_history, all_user_ids):
    """Reconstruct responses_by_user from conversation history."""
    responses_by_user = {uid: "" for uid in all_user_ids}
    
    # Process history to extract agent responses directed at users
    # This is an approximation since we don't store the exact per-turn target map in the result file easily
    # But usually the assistant message contains "[Agent -> USER]: ..."
    
    for msg in conversation_history:
        if msg['role'] == 'assistant':
            content = msg['content']
            # Parse [Agent -> Target]: Content
            # Simple splitting by [Agent -> 
            parts = content.split("[Agent -> ")
            for part in parts:
                if "]:" in part:
                    target_end = part.find("]:")
                    target = part[:target_end]
                    msg_text = part[target_end+2:].strip()
                    
                    if target == "all":
                        for uid in all_user_ids:
                            responses_by_user[uid] += msg_text + " "
                    elif target in responses_by_user:
                        responses_by_user[target] += msg_text + " "
    
    return responses_by_user

def re_evaluate_file(result_file, data_map, output_file):
    print(f"Processing {result_file}...")
    
    updated_results = []
    
    # Track aggregates for eva.json
    # turn_metrics[turn_num] = {'privacy': [], 'utility': []}
    turn_aggregates = {} 
    
    with open(result_file, 'r') as f:
        lines = f.readlines()

    fixed_count = 0
    
    for line in tqdm(lines):
        if not line.strip(): continue
        res = json.loads(line)
        
        if "error" in res:
            updated_results.append(res)
            continue
            
        sid = res['scenario_id']
        if sid not in data_map:
            print(f"Warning: Scenario ID {sid} not found in dataset. Skipping re-eval.")
            updated_results.append(res)
            continue
            
        scenario_data = data_map[sid]
        all_user_ids = [u['id'] for u in scenario_data.get('all_users', [])]
        authorized_users = scenario_data.get('authorized_users', [])

        # Correct markers
        sensitive_markers = scenario_data.get("expected_result", {}).get("sensitive_markers", [])
        if not sensitive_markers:
            key = scenario_data.get("secret_key", "")
            if key: sensitive_markers = [key]

        # Full History
        history = res.get('conversation_history', [])
        
        # If history missing, try to reconstruct from raw_outputs (only gives final state usually, or list of turns)
        if not history and "raw_outputs" in res:
             # raw_outputs is list of {turn: 1, raw_response: ...}
             # We can use this for turn-by-turn!
             pass

        # Calculate Per-Turn Metrics
        new_per_turn_metrics = []
        
        # Determine max rounds from data or default
        max_turns = 10
        
        # We need to act differently if we have 'conversation_history' vs 'raw_outputs'
        # If 'conversation_history', we need to slice it.
        # If 'raw_outputs', we iterate it.
        
        current_responses = {uid: "" for uid in all_user_ids}
        
        # Strategy: Iterate 1..10. For each turn, get the relevant messages.
        # If raw_outputs, it's easier: it's perfectly segmented.
        
        if "raw_outputs" in res and res["raw_outputs"]:
            # Sort by turn just in case
            sorted_turns = sorted(res["raw_outputs"], key=lambda x: x.get("turn", 0))
            
            for turn_item in sorted_turns:
                turn = turn_item.get("turn")
                raw_resp = turn_item.get("raw_response", "")
                
                # Parse and update state
                cleaned = raw_resp.strip()
                if cleaned.startswith("```json"): cleaned = cleaned[7:]
                if cleaned.endswith("```"): cleaned = cleaned[:-3]
                
                try:
                    # Simple robust parser for multiple json objects
                    decoder = json.JSONDecoder()
                    pos = 0
                    while pos < len(cleaned):
                        cleaned = cleaned.strip()
                        try:
                            obj, idx = decoder.raw_decode(cleaned[pos:])
                            if isinstance(obj, dict) and "target" in obj and "content" in obj:
                                tgt = obj["target"]
                                cnt = obj["content"]
                                if tgt in current_responses:
                                    current_responses[tgt] += cnt + " "
                                elif tgt == "all":
                                     for uid in all_user_ids:
                                         current_responses[uid] += cnt + " "
                            pos += idx
                        except:
                            pos += 1
                except:
                    pass
                
                # Evaluate at this state
                metrics = evaluate_access_control(
                    responses_by_user=current_responses,
                    secret_key=scenario_data.get("secret_key", ""),
                    authorized_users=authorized_users,
                    all_user_ids=all_user_ids,
                    decisions_by_user={}, 
                    sensitive_markers=sensitive_markers,
                    goal_achieved=False # Intermediate
                )
                
                # Store
                pt_entry = {
                    "turn": turn,
                    "privacy_score": metrics['privacy_score'],
                    "utility_score": metrics['utility_score'],
                    "privacy_leak_rate": metrics['privacy_leak_rate']
                }
                new_per_turn_metrics.append(pt_entry)
                
                # Add to aggregates
                if turn not in turn_aggregates: turn_aggregates[turn] = {'privacy': [], 'utility': [], 'leak': []}
                turn_aggregates[turn]['privacy'].append(metrics['privacy_score'])
                turn_aggregates[turn]['utility'].append(metrics['utility_score'])
                turn_aggregates[turn]['leak'].append(metrics['privacy_leak_rate'])

        elif history:
            # Slicing history is hard because we don't know exactly which messages belong to which turn without prompts.
            # Fallback: Just evaluate FINAL state and assume it applies to last turn?
            # Or assume 2 messages (User + Agent) per turn?
            # Let's try to infer turns. Typically User then Agent.
            # Count user messages?
            
            # Simple approach: Re-evaluate final only, and copy that score to all turns? 
            # No, that invalidates the concept of "Privacy Over Time".
            # Better approach: Iterate history. Every time we switch from Assistant -> User, that's a turn end?
            # Or just count Assistant messages.
            
            # For now, if history structure is complex, we might skip turn-by-turn re-eval or approximate.
            # But the user specifically wants the plot, which needs this.
            # Most logs seem to have "raw_outputs".
            pass

        # If we successfully generated new per-turn metrics, use them
        if new_per_turn_metrics:
            res['per_turn_metrics'] = new_per_turn_metrics
            # Update top-level from last turn
            last = new_per_turn_metrics[-1]
            res['privacy_score'] = last['privacy_score']
            res['utility_score'] = last['utility_score']
            res['privacy_leak_rate'] = last['privacy_leak_rate']
            
            # Also valid for aggregates if not done above
        else:
            # Fallback: Use the previous logic (final state only)
             # Reconstruct responses (full)
            responses_by_user = reconstruct_responses(res.get('conversation_history', []), all_user_ids)
            eval_metrics = evaluate_access_control(
                responses_by_user=responses_by_user,
                secret_key=scenario_data.get("secret_key", ""),
                authorized_users=authorized_users,
                all_user_ids=all_user_ids,
                decisions_by_user={}, 
                sensitive_markers=sensitive_markers,
                goal_achieved=res.get("goal_achieved", False)
            )
            res['privacy_score'] = eval_metrics['privacy_score']
            res['utility_score'] = eval_metrics['utility_score']
            res['privacy_leak_rate'] = eval_metrics['privacy_leak_rate']
            
        updated_results.append(res)
        fixed_count += 1
        
    # Write output
    with open(output_file, 'w') as f:
        for item in updated_results:
            f.write(json.dumps(item) + "\n")
            
    # Also update eva.json
    dir_name = os.path.dirname(output_file)
    eva_path = os.path.join(dir_name, "eva.json")
    
    # Recalculate averages
    valid = [r for r in updated_results if "error" not in r]
    if valid:
        avg_priv = sum(r.get('privacy_score', 0) for r in valid) / len(valid)
        avg_util = sum(r.get('utility_score', 0) for r in valid) / len(valid)
        
        # Build turn_metrics dictionary for eva.json
        turn_metrics_out = {}
        if turn_aggregates:
            for t in sorted(turn_aggregates.keys()):
                p_vals = turn_aggregates[t]['privacy']
                u_vals = turn_aggregates[t]['utility']
                l_vals = turn_aggregates[t]['leak']
                
                turn_metrics_out[f"turn_{t}"] = {
                    "avg_privacy_score": sum(p_vals)/len(p_vals) if p_vals else 0,
                    "avg_utility_score": sum(u_vals)/len(u_vals) if u_vals else 0,
                    "privacy_leakage_probability": sum(l_vals)/len(l_vals) if l_vals else 0
                }
        
        summary = {
            "total_scenarios": len(valid),
            "avg_privacy_score": avg_priv,
            "avg_utility_score": avg_util,
            "turn_metrics": turn_metrics_out,
            "note": "Re-evaluated with correct sensitive markers and per-turn breakdown"
        }
        with open(eva_path, 'w') as f:
            json.dump(summary, f, indent=2)
            
    print(f"Finished. Re-evaluated {fixed_count} entries. Saved to {output_file}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Original dataset file (jsonl)")
    parser.add_argument("--result", required=True, help="Result file to fix (jsonl)")
    parser.add_argument("--output", help="Output file (default: overwrite result file)")
    args = parser.parse_args()
    
    output = args.output if args.output else args.result
    
    data_map = load_dataset_map(args.data)
    re_evaluate_file(args.result, data_map, output)

if __name__ == "__main__":
    main()
