import json
import os
import sys
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs): return iterable

from muses_bench.utils.llm_utils import call_llm_with_retry
from muses_bench.utils.format_utils import build_instruction_following_system_prompt, parse_training_format_response
from muses_bench.utils.file_utils import setup_output_structure, load_existing_results

# Ensure IHEval is in path
IHEVAL_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../IHEval/src"))
IHEVAL_EVAL_SRC = os.path.join(IHEVAL_SRC, "rule_following/evaluate")

if IHEVAL_SRC not in sys.path:
    sys.path.append(IHEVAL_SRC)
if IHEVAL_EVAL_SRC not in sys.path:
    sys.path.append(IHEVAL_EVAL_SRC)

try:
    from rule_following.evaluate import instructions_registry
    from rule_following.evaluate import instructions_util
    from rule_following.evaluate import instructions
except ImportError as e:
    print(f"[WARNING] Could not import IHEval modules from {IHEVAL_SRC}. Validation will fail. Error: {e}")

# Lock for thread-safe file writing
io_lock = threading.Lock()

def process_single_scenario(line, model, provider, llm_client, lora_request, use_training_format, debug, processed_ids):
    if not line.strip(): return None
    data = json.loads(line)
    scenario_id = data.get('id')
    
    if scenario_id in processed_ids:
        return None
    
    if debug:
        print(f"\nRunning Scenario: {scenario_id}")
    
    try:
        # 1. Construct Prompt
        base_system_prompt = data.get("system_prompt", "You are a helpful assistant serving multiple users.")
        users = data.get("users", [])
        
        # Build system prompt using helper function
        system_prompt = build_instruction_following_system_prompt(
            base_system_prompt, 
            users, 
            use_training_format=use_training_format
        )
        
        # Build messages based on format
        if use_training_format:
            # Training format: separate user_UserName messages
            messages = [{"role": "system", "content": system_prompt}]
            for user in users:
                user_id = user.get("id", "User")
                instructions = user.get("instructions", [])
                if instructions:
                    user_content = "\n".join(instructions)
                    messages.append({
                        "role": f"user_{user_id}",
                        "content": user_content
                    })
        else:
            # Evaluation format: single user message with XML tags
            conversation_text = ""
            for user in users:
                user_id = user.get("id", "User")
                for instr in user.get("instructions", []):
                    conversation_text += f"<{user_id}>{instr}</{user_id}>\n"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": conversation_text}
            ]
        
        if debug:
             with io_lock:
                print("\n" + "="*70)
                print(f"[DEBUG] MODEL INPUT for {scenario_id}")
                print("="*70)

        response = call_llm_with_retry(
            model=model,
            provider=provider,
            messages=messages,
            temperature=1.0,
            llm_client=llm_client,
            lora_request=lora_request
        )
        
        raw_output = response.choices[0].message.content
        
        if debug:
             with io_lock:
                print(f"[OUTPUT] {scenario_id}")
                print(raw_output)
                print("-" * 40)

        # 3. Parse Output (JSON or @ format)
        user_responses = {}
        
        if use_training_format:
            # Parse @ format responses
            user_responses = parse_training_format_response(raw_output)
        else:
            # Parse JSON format responses
            try:
                # Cleanup markdown code blocks if present
                clean_output = raw_output.strip()
                if clean_output.startswith("```json"):
                    clean_output = clean_output[7:]
                if clean_output.startswith("```"):
                    clean_output = clean_output[3:]
                if clean_output.endswith("```"):
                    clean_output = clean_output[:-3]
                clean_output = clean_output.strip()
                
                user_responses = json.loads(clean_output)
            except json.JSONDecodeError:
                if debug:
                     with io_lock:
                        print(f"[WARNING] Failed to parse JSON output for {scenario_id}. Raw output: {raw_output[:100]}...")
                # If JSON parsing fails, we treat it as empty or all failed
                user_responses = {}

        # 4. Validate using IHEval per user
        instruction_results = []
        
        valid_count = 0
        total_count = 0
        
        weighted_valid_count = 0
        weighted_total_count = 0
        
        # Determine mode and max authority for this example
        meta = data.get("meta", {})
        mode = meta.get("mode", "aligned")
        
        max_auth = -1
        if mode == "conflict":
            for u in users:
                auth = float(u.get("authority", 0))
                if auth > max_auth:
                    max_auth = auth

        for user in users:
            user_id = user.get("id")
            # Default authority to 1 if missing
            user_authority = float(user.get("authority", 1.0))
            
            # In conflict mode, skip users who are not the highest authority
            is_eval_target = True
            if mode == "conflict" and user_authority < max_auth:
                is_eval_target = False
            
            response_val = user_responses.get(user_id, "")
            
            # FIX: Ensure response is a string for regex validators
            if not isinstance(response_val, str):
                # If it's a list or dict, convert to JSON string representation
                # This allows validators checking for "Python list" syntax to pass
                response_text = json.dumps(response_val, ensure_ascii=False)
            else:
                response_text = response_val
            
            if not response_text:
                if user_id not in user_responses:
                    # if debug: print(f"  [MISSING] No response found for user {user_id}")
                    pass
            
            # Get constraints for this user
            original_ans = user.get("original_answer", {})
            if isinstance(original_ans, dict):
                inst_ids = original_ans.get("instruction_id_list", [])
                kwargs_list = original_ans.get("kwargs", [])
                
                for i, inst_id in enumerate(inst_ids):
                    if is_eval_target:
                        total_count += 1
                        weighted_total_count += user_authority
                    
                    kw = kwargs_list[i] if i < len(kwargs_list) else {}
                    
                    passed = False
                    error_msg = ""
                    
                    if 'instructions_registry' in globals() and inst_id in instructions_registry.INSTRUCTION_DICT:
                        try:
                            instruction_cls = instructions_registry.INSTRUCTION_DICT[inst_id]
                            instruction = instruction_cls(inst_id)
                            instruction.build_description(**kw)
                            
                            # Check ONLY this user's response
                            passed = instruction.check_following(response_text)
                            
                        except Exception as e:
                            error_msg = str(e)
                            if debug:
                                 with io_lock:
                                    print(f"  [ERROR] Validating {inst_id} for {user_id}: {e}")
                    else:
                        error_msg = "Unknown ID or Registry Missing"
                        if debug:
                             with io_lock:
                                print(f"  [ERROR] Unknown instruction ID: {inst_id}")

                    if passed:
                        if is_eval_target:
                            valid_count += 1
                            weighted_valid_count += user_authority
                    else:
                         if is_eval_target:
                             pass
                         else:
                             pass

                    instruction_results.append({
                        "user_id": user_id,
                        "authority": user_authority,
                        "instruction_id": inst_id,
                        "kwargs": kw,
                        "passed": passed,
                        "error": error_msg
                    })

        accuracy = valid_count / total_count if total_count > 0 else 0.0
        weighted_accuracy = weighted_valid_count / weighted_total_count if weighted_total_count > 0 else 0.0
        
        metrics = {
            "accuracy": accuracy,
            "weighted_accuracy": weighted_accuracy,
            "num_instructions": total_count,
            "num_followed": valid_count,
            "all_passed": (valid_count == total_count) and (total_count > 0)
        }
        
        if debug:
             with io_lock:
                print(f"Metrics: {metrics}")

        res = {
            "scenario_id": scenario_id,
            "model_output": raw_output,
            "instruction_results": instruction_results,
            "metrics": metrics
        }
        return res
        
    except Exception as e:
        print(f"[ERROR] Failed to run scenario {scenario_id}: {e}")
        # traceback.print_exc()
        res = {
            "scenario_id": scenario_id,
            "error": str(e),
            "metrics": {"accuracy": 0.0}
        }
        return res


def run_instruction_following_batch(data_file: str, model: str, provider: str, user_model: str = None, output_file: str = None, max_turns: int = 15, debug: bool = False, llm_client=None, lora_request=None, use_training_format: bool = False):
    """Run batch evaluation for Multi-User Instruction Following scenario."""
    print(f"\nRunning Instruction Following Batch: {data_file}")
    print(f"IHEval Path: {IHEVAL_SRC}")
    print(f"Training Format: {use_training_format}")
    
    with open(data_file, 'r') as f:
        lines = f.readlines()
        
    if debug:
        print("[DEBUG] Running in debug mode - processing only first 3 lines.")
        lines = lines[:3]
        
    results = []
    processed_ids = set()
    
    log_file, eva_file = setup_output_structure("instruction_following", model, data_file, max_turns, debug, output_file)

    # Resume capability
    results, processed_ids = load_existing_results(str(log_file))

    # Ensure instructions_registry is available
    if 'instructions_registry' not in globals():
         print("[ERROR] instructions_registry not available. Cannot validate.")

    # Determine max_workers for parallel execution
    max_workers = 16 if not debug else 1
    if provider == "vllm":
        max_workers = 1 
    
    print(f"Executing with max_workers={max_workers}")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for line in lines:
            futures.append(
                executor.submit(
                    process_single_scenario, 
                    line, model, provider, llm_client, lora_request, use_training_format, debug, processed_ids
                )
            )
            
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
                            
                    # Incremental summary
                    if eva_file:
                        acc_values = [r.get("metrics", {}).get("accuracy", 0) for r in results]
                        avg_acc = sum(acc_values) / len(acc_values) if acc_values else 0
                        
                        summary_data = {
                            "total_scenarios": len(results),
                            "avg_accuracy": avg_acc,
                            "model": model,
                            "provider": provider,
                            "data_file": data_file
                        }
                        with open(eva_file, 'w') as f_eva:
                            json.dump(summary_data, f_eva, indent=2)

    # Final print
    acc_values = [r.get("metrics", {}).get("accuracy", 0) for r in results]
    avg_acc = sum(acc_values) / len(acc_values) if acc_values else 0
    print(f"\nFinal Average Accuracy: {avg_acc:.2%}")
