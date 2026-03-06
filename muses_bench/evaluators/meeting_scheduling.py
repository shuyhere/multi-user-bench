import json
import os
import re
import tempfile
import traceback
import threading
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs): return iterable

from muses_bench.envs.conversation_env import ConversationEnv
from muses_bench.core.types import Action
from muses_bench.metrics.meeting_scheduling_metrics import evaluate_meeting_scheduling, print_meeting_summary
from muses_bench.utils.llm_utils import call_llm_with_retry
from muses_bench.utils.file_utils import setup_output_structure, load_existing_results
from muses_bench.utils.format_utils import build_instruction_following_system_prompt, parse_training_format_response, convert_access_control_system_prompt

# Lock for thread-safe file writing
io_lock = threading.Lock()

def run_meeting_scheduling_conversational(scenario_data: Dict, model: str, provider: str, user_model: str = None, max_turns: int = 15, llm_client=None, lora_request=None, use_training_format: bool = False):
    """Run a single meeting scheduling scenario using ConversationEnv."""
    
    all_user_ids = [u["id"] for u in scenario_data.get("users", [])]
    
    # Generate initial messages if needed
    initial_messages = {}
    
    # Build system prompt for agent
    system_prompt = scenario_data.get("system_prompt", scenario_data.get("prompt", ""))
    
    # Convert to training format if needed
    if use_training_format:
        users_data = scenario_data.get("users", [])
        system_prompt = convert_access_control_system_prompt(system_prompt, users_data, use_training_format=True)
    
    # Construct env scenario
    env_scenario = {
        "id": scenario_data.get("id", "unknown"),
        "scenario": "MeetingScheduling_Complex",
        "system_prompt": system_prompt,
        "users": scenario_data.get("users", []),
        "initial_messages": initial_messages,
        "task_query": "Schedule a meeting.",
        "params": scenario_data.get("params", {})
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(env_scenario, f)
        temp_file = f.name
        
    try:
        env = ConversationEnv(
            temp_file, 
            user_model=user_model or model, 
            provider=provider, 
            llm_client=llm_client, 
            lora_request=lora_request
        )
        obs = env.reset()
        
        conversation_history = [{"role": "system", "content": system_prompt}]
        raw_outputs = []
        
        # Tracking
        goal_achieved = False
        final_schedule = None
        attendees = []
        
        cumulative_responses_by_user = {uid: "" for uid in all_user_ids}
        
        # Force hardcoded initial agent message
        initial_agent_msg = "Hello! I am your AI Facilitator. We need to schedule a meeting. Please provide your availability for this week."
        conversation_history.append({"role": "assistant", "content": initial_agent_msg})
        
        initial_action = Action(
            name="respond",
            arguments={
                "content": initial_agent_msg,
                "target_user_id": "all",
                "individual_targets": {uid: [initial_agent_msg] for uid in all_user_ids}
            }
        )
        obs, _, done, info = env.step(initial_action)
        
        turn = 0
        
        for turn in range(max_turns):
            
            # 1. User Messages
            if use_training_format:
                for uid, observation in obs.items():
                    if uid not in ["system", "tool_result"]:
                        content = getattr(observation, 'content', str(observation))
                        if content.startswith(f"[{uid}]:"):
                            content = content[len(uid)+3:].strip()
                        elif content.startswith(f"{uid}:"):
                            content = content[len(uid)+1:].strip()
                        elif content.startswith(f"@{uid}:"):
                            content = content[len(uid)+2:].strip()
                        elif content.startswith(f"<{uid}>") and content.endswith(f"</{uid}>"):
                            content = content[len(uid)+2 : -(len(uid)+3)].strip()
                        
                        conversation_history.append({
                            "role": f"user_{uid}",
                            "content": content
                        })
            else:
                user_messages = []
                for uid, observation in obs.items():
                    if uid not in ["system", "tool_result"]:
                        content = getattr(observation, 'content', str(observation))
                        user_messages.append(f"[{uid}]: {content}")
                
                if user_messages:
                    combined_msg = "\n".join(user_messages)
                    conversation_history.append({"role": "user", "content": combined_msg})
            
            # 2. Agent Action
            response = call_llm_with_retry(
                model=model, provider=provider,
                messages=conversation_history, temperature=1.0,
                llm_client=llm_client, lora_request=lora_request
            )
            agent_response = response.choices[0].message.content
            
            raw_outputs.append({"turn": turn+1, "raw": agent_response})
            conversation_history.append({"role": "assistant", "content": agent_response})
            
            # 3. Parse Response
            target_messages = {}
            json_objects = []
            
            if use_training_format:
                 user_responses = parse_training_format_response(agent_response)
                 for uid, msg in user_responses.items():
                     if uid not in target_messages: target_messages[uid] = []
                     target_messages[uid].append(msg)
            
            cleaned = agent_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            decoder = json.JSONDecoder()
            pos = 0
            while pos < len(cleaned):
                cleaned = cleaned.strip()
                try:
                    obj, idx = decoder.raw_decode(cleaned[pos:])
                    json_objects.append(obj)
                    pos += idx
                except json.JSONDecodeError:
                    pos += 1
            
            for obj in json_objects:
                if isinstance(obj, dict):
                    if obj.get("goal_achieved"):
                        goal_achieved = True
                        final_schedule = obj.get("final_schedule")
                        attendees = obj.get("attendees", [])
                    
                    if "target" in obj and "content" in obj:
                        tgt = obj["target"]
                        msg = obj["content"]
                        
                        if tgt == "all":
                             for u in all_user_ids:
                                 if u not in target_messages: target_messages[u] = []
                                 target_messages[u].append(msg)
                        else:
                             if tgt not in target_messages: target_messages[tgt] = []
                             target_messages[tgt].append(msg)
            
            # 4. Step Environment
            action_args = {
                "content": agent_response,
                "target_user_id": "all",
                "individual_targets": target_messages
            }
            action = Action(name="respond", arguments=action_args)
            
            obs, _, done, info = env.step(action)
            
            if goal_achieved:
                break
        
        final_turns = turn + 1
        eval_metrics = evaluate_meeting_scheduling(
            responses_by_user=cumulative_responses_by_user,
            final_schedule=final_schedule,
            user_configs=scenario_data.get("users", []),
            goal_achieved=goal_achieved,
            attendees=attendees,
            total_turns=final_turns
        )
        
        return {
            "scenario_id": scenario_data.get("id"),
            "metrics": eval_metrics,
            "goal_achieved": goal_achieved,
            "raw_outputs": raw_outputs,
            "history": conversation_history
        }

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

def process_single_scenario(line, model, provider, user_model, max_turns, llm_client, lora_request, use_training_format, debug, processed_ids):
    if not line.strip(): return None
    data = json.loads(line)
    scenario_id = data.get('id')
    
    if scenario_id in processed_ids:
        return None
        
    if debug:
         with io_lock:
            print(f"\nRunning Scenario: {scenario_id}")
    
    try:
        res = run_meeting_scheduling_conversational(
            data, model, provider, user_model, max_turns, 
            llm_client=llm_client, lora_request=lora_request, 
            use_training_format=use_training_format
        )
    except Exception as e:
        with io_lock:
            print(f"[ERROR] Failed to run scenario {scenario_id}: {e}")
        # Create error result
        res = {
            "scenario_id": scenario_id,
            "metrics": {
                "success_rate": 0.0,
                "utility_score": 0.0,
                "turns_taken": 0,
                "error": str(e)
            },
            "raw_outputs": [],
            "history": []
        }
    return res

def run_meeting_scheduling_batch(data_file: str, model: str, provider: str, user_model: str = None, output_file: str = None, max_turns: int = 15, debug: bool = False, llm_client=None, lora_request=None, use_training_format: bool = False):

    print(f"\nRunning Meeting Scheduling Batch: {data_file}")
    print(f"Debug Mode: {debug}")
    print(f"Training Format: {use_training_format}")
    
    with open(data_file, 'r') as f:
        lines = f.readlines()
        
    if debug:
        print("[DEBUG] Running in debug mode - processing only first 3 lines.")
        lines = lines[:3]
        
    results = []
    processed_ids = set()
    
    log_file, eva_file = setup_output_structure("meeting_scheduling", model, data_file, max_turns, debug, output_file)

    # Resume capability
    results, processed_ids = load_existing_results(str(log_file))

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
                    line, model, provider, user_model, max_turns, llm_client, lora_request, use_training_format, debug, processed_ids
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
                    
                    # Update stats inside lock
                    temp_results = results
                    temp_success_count = sum(1 for r in temp_results if r["metrics"].get("success_rate") == 1.0)
                    temp_total = len(temp_results)
                    
                    if eva_file:
                        # Simplified incremental metric dump (full stats calculated at end)
                         summary_data = {
                            "total_scenarios": temp_total,
                            "success_count": temp_success_count,
                             "success_rate": temp_success_count / temp_total if temp_total > 0 else 0,
                            "model": model,
                            "provider": provider,
                            "data_file": data_file
                        }
                         with open(eva_file, 'w') as f_eva:
                            json.dump(summary_data, f_eva, indent=2)

    # Final Summary
    success_count = sum(1 for r in results if r["metrics"].get("success_rate") == 1.0)
    print(f"\nBatch Complete. Success: {success_count}/{len(results)}")
    
    # Calculate more detailed metrics for final report
    aggregated_metrics = {}
    target_metric_keys = ["success_rate", "optional_attendance", "utility_score"]
    final_metrics = {}
    
    if results:
        all_keys = set()
        for r in results:
            all_keys.update(r["metrics"].keys())
        
        for key in all_keys:
            values = [r["metrics"].get(key) for r in results if r["metrics"].get(key) is not None]
            if values and isinstance(values[0], (int, float)):
                avg_val = sum(values) / len(values)
                aggregated_metrics[f"avg_{key}"] = avg_val
                if key in target_metric_keys:
                    final_metrics[key] = avg_val
                    
    if eva_file:
        summary_data = {
            "total_scenarios": len(results),
            "success_count": success_count,
            "success_rate": success_count / len(results) if results else 0,
            "metrics_summary": aggregated_metrics,
            "utility_metrics": final_metrics,
            "model": model,
            "provider": provider,
            "max_turns": max_turns
        }
        with open(eva_file, 'w') as f_eva:
            json.dump(summary_data, f_eva, indent=2)
            
    return results
