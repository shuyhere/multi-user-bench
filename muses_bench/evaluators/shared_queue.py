import json
import os
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs): return iterable

from muses_bench.utils.llm_utils import call_llm_with_retry
from muses_bench.metrics.shared_queue_metrics import evaluate_shared_queue, print_shared_queue_summary
from muses_bench.utils.file_utils import setup_output_structure, load_existing_results
from muses_bench.utils.format_utils import convert_to_training_format_prompt, convert_system_prompt_to_training_format

# Lock for thread-safe file writing
io_lock = threading.Lock()

def process_single_scenario(line, model, provider, llm_client, lora_request, use_training_format, debug, processed_ids, log_file, eva_file):
    if not line.strip(): return None
    data = json.loads(line)
    scenario_id = data.get('id')
    
    if scenario_id in processed_ids:
        return None
    
    if debug:
        print(f"\nRunning Scenario: {scenario_id}")
    
    try:
        # Get system prompt from data
        system_prompt = data.get("system_prompt", "")
        users_data = data.get("users", [])
        
        # Convert system prompt if using training format
        if use_training_format:
            system_prompt = convert_system_prompt_to_training_format(system_prompt, users_data, use_training_format=True)
        
        # Build user prompt with appropriate format
        if use_training_format:
            # Training format: separate message per user with role "user_UserName"
            user_prompt = None  # Not used in training format
        else:
            # Evaluation format: single combined message with XML tags
            user_prompt = convert_to_training_format_prompt(users_data, use_training_format=False)
        
        # Build messages array based on format
        if use_training_format:
            # Training format: system + multiple user_UserName messages
            messages = [{"role": "system", "content": system_prompt}]
            for user in users_data:
                user_id = user.get("id", "Unknown")
                instructions = user.get("instructions", [])
                if instructions:
                    # Combine all instructions from this user into one message
                    user_content = "\n".join(instructions)
                    messages.append({
                        "role": f"user_{user_id}",
                        "content": user_content
                    })
        else:
            # Evaluation format: system + single user message with XML tags
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        
        # Debug: Print input
        if debug:
             with io_lock:
                print("\n" + "="*70)
                print(f"[DEBUG] MODEL INPUT for {scenario_id}")
                print("="*70)
                
        # Make LLM call
        response = call_llm_with_retry(
            model=model,
            provider=provider,
            messages=messages,
            temperature=1.0,
            llm_client=llm_client,
            lora_request=lora_request
        )
        
        raw_output = response.choices[0].message.content
        
        # Debug: Print output
        if debug:
             with io_lock:
                print("\n" + "="*70)
                print(f"[DEBUG] MODEL OUTPUT for {scenario_id}")
                print("="*70)
                print(raw_output)
                print("="*70 + "\n")
        
        # Parse JSON output
        try:
            # Extract JSON from markdown code blocks if present
            if "```json" in raw_output:
                json_start = raw_output.find("```json") + 7
                json_end = raw_output.find("```", json_start)
                json_str = raw_output[json_start:json_end].strip()
            elif "```" in raw_output:
                json_start = raw_output.find("```") + 3
                json_end = raw_output.find("```", json_start)
                json_str = raw_output[json_start:json_end].strip()
            else:
                json_str = raw_output.strip()
            
            model_output = json.loads(json_str)
        except json.JSONDecodeError as e:
            if debug:
                 with io_lock:
                    print(f"[ERROR] Failed to parse JSON from model output: {e}")
                    print(f"Raw output: {raw_output[:500]}")
            model_output = {"accepted_instructions": [], "rejected_instructions": []}
        
        # Build mapping from reference numbers to full IDs
        # Ground truth uses full IDs like "Heidi_task_1234"
        # Model outputs reference numbers like "1234"
        ref_to_full_id = {}
        ground_truth = data.get("expected_output", {})
        
        # Extract all instruction IDs from ground truth (for mapping purposes only)
        # Use list() to create a copy, not modify the original
        all_gt_ids = list(ground_truth.get("accepted_instructions", []))
        for rej in ground_truth.get("rejected_instructions", []):
            if isinstance(rej, dict):
                all_gt_ids.append(rej.get("id", ""))
            else:
                all_gt_ids.append(rej)
        
        # Build mapping: reference number -> full ID
        for full_id in all_gt_ids:
            if "_task_" in full_id:
                ref_num = full_id.split("_task_")[-1]
                ref_to_full_id[ref_num] = full_id
        
        # Convert model output reference numbers to full IDs
        model_accepted_refs = model_output.get("accepted_instructions", [])
        model_accepted_full = [ref_to_full_id.get(ref, ref) for ref in model_accepted_refs]
        
        model_rejected_refs = model_output.get("rejected_instructions", [])
        model_rejected_full = []
        for rej in model_rejected_refs:
            if isinstance(rej, dict):
                ref = rej.get("id", "")
                full_id = ref_to_full_id.get(ref, ref)
                model_rejected_full.append({"id": full_id, "reason": rej.get("reason", "")})
            else:
                full_id = ref_to_full_id.get(rej, rej)
                model_rejected_full.append(full_id)
        
        # Create normalized model output with full IDs
        model_output_normalized = {
            "accepted_instructions": model_accepted_full,
            "rejected_instructions": model_rejected_full
        }
        
        # Evaluate
        metrics = evaluate_shared_queue(model_output_normalized, ground_truth)
        
        # Print metrics
        if debug:
             with io_lock:
                print_shared_queue_summary(metrics, verbose=True)
        
        res = {
            "scenario_id": scenario_id,
            "model_output": model_output,
            "ground_truth": ground_truth,
            "metrics": metrics,
            "raw_output": raw_output
        }
        
        return res
        
    except Exception as e:
        print(f"[ERROR] Failed to run scenario {scenario_id}: {e}")
        # traceback.print_exc()
        res = {
            "scenario_id": scenario_id,
            "metrics": {
                "MAIS": 0.0,
                "gt_accepted_count": 0,
                "model_accepted_count": 0,
                "correct_accepted_count": 0,
                "error": str(e)
            },
            "model_output": {},
            "ground_truth": {},
            "raw_output": ""
        }
        return res

def run_shared_queue(data_file: str, model: str, provider: str, user_model: str = None, output_file: str = None, max_turns: int = 5, debug: bool = False, llm_client=None, lora_request=None, use_training_format: bool = False):
    """Run batch evaluation for Shared Queue scenario (Chain of Command)."""
    print(f"\nRunning Shared Queue Batch: {data_file}")
    print(f"Debug Mode: {debug}")
    print(f"Training Format: {use_training_format}")
    
    with open(data_file, 'r') as f:
        lines = f.readlines()
        
    if debug:
        print("[DEBUG] Running in debug mode - processing only first 3 lines.")
        lines = lines[:3]
        
    results = []
    processed_ids = set()
    
    log_file, eva_file = setup_output_structure("shared_queue", model, data_file, max_turns, debug, output_file)

    # Resume capability: Load existing results
    results, processed_ids = load_existing_results(str(log_file))

    # Determine max_workers for parallel execution
    max_workers = 16 if not debug else 1
    if provider == "vllm":
        # vLLM internal batching usually handles concurrency, but we can set a small number if using AsyncLLMEngine (unlikely here)
        # If using standard LLM engine, calls might be sequential unless batched. 
        # But here we are making separate API calls? 
        # If llm_client is passed, it might be the vLLM engine.
        # If it's vLLM engine, parallel calls might be unsafe if the engine isn't async wrapped.
        # However, looking at vllm_client.py, it seems to just call generate.
        # Let's assume ThreadPool is safe for requests (OpenAI/Litellm) but maybe careful for local vLLM.
        # Defaulting to 1 for vLLM just in case to avoid shared state issues, unless we know it's safe.
        max_workers = 1 
    
    print(f"Executing with max_workers={max_workers}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for line in lines:
            futures.append(
                executor.submit(
                    process_single_scenario, 
                    line, model, provider, llm_client, lora_request, use_training_format, debug, processed_ids, log_file, eva_file
                )
            )
        
        # Process results as they complete
        iterator = as_completed(futures)
        if not debug:
            iterator = tqdm(iterator, total=len(futures), desc="Processing Scenarios")
            
        for future in iterator:
            res = future.result()
            if res:
                with io_lock:
                    results.append(res)
                    
                    if log_file:
                        with open(log_file, 'a') as f_out:
                            f_out.write(json.dumps(res) + "\n")
                    
                    # Incremental update for eva.json
                    # Note: Calculating averages on every step might be slow for massive batches, 
                    # but fine for typical eval sizes (hundreds).
                    # We do it inside lock to ensure consistent read/write.
                    
                    temp_results = results
                    temp_total = len(temp_results)
                    
                    mais_values = [r["metrics"].get("MAIS", 0) for r in temp_results]
                    avg_mais = sum(mais_values) / len(mais_values) if mais_values else 0
                    
                    acc_values = [r["metrics"].get("Accuracy", 0) for r in temp_results]
                    avg_acc = sum(acc_values) / len(acc_values) if acc_values else 0
                    
                    f1_values = [r["metrics"].get("F1_Score", 0) for r in temp_results]
                    avg_f1 = sum(f1_values) / len(f1_values) if f1_values else 0
                    
                    if eva_file:
                        summary_data = {
                            "total_scenarios": temp_total,
                            "avg_MAIS": avg_mais,
                            "avg_Accuracy": avg_acc,
                            "avg_F1_Score": avg_f1,
                            "model": model,
                            "provider": provider,
                            "data_file": data_file
                        }
                        with open(eva_file, 'w') as f_eva:
                            json.dump(summary_data, f_eva, indent=2)

    # Final Summary
    print(f"\n{'=' * 70}")
    print(f"Batch Complete. Processed: {len(results)} scenarios")
    print(f"{'=' * 70}")
    
    # Calculate final metrics
    mais_values = [r["metrics"].get("MAIS", 0) for r in results]
    avg_mais = sum(mais_values) / len(mais_values) if mais_values else 0
    
    acc_values = [r["metrics"].get("Accuracy", 0) for r in results]
    avg_acc = sum(acc_values) / len(acc_values) if acc_values else 0
    
    f1_values = [r["metrics"].get("F1_Score", 0) for r in results]
    avg_f1 = sum(f1_values) / len(f1_values) if f1_values else 0
    
    print(f"\nAverage F1 Score: {avg_f1:.2%}")
    print(f"Average Accuracy: {avg_acc:.2%}")
    print(f"Average MAIS:     {avg_mais:.2%}")
    
    # Save final evaluation summary
    if eva_file:
        summary_data = {
            "total_scenarios": len(results),
            "avg_MAIS": avg_mais,
            "avg_Accuracy": avg_acc,
            "avg_F1_Score": avg_f1,
            "model": model,
            "provider": provider,
            "data_file": data_file
        }
        with open(eva_file, 'w') as f_eva:
            json.dump(summary_data, f_eva, indent=2)
        print(f"Evaluation summary saved to: {eva_file}")
