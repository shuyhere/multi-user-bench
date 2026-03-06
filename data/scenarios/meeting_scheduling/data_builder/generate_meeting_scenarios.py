import json
import random
import argparse
import os
from pathlib import Path

NAMES = [
    "Jair", "Yahir", "Oliver", "Hiroshi", "Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Heidi", "Ivan", "Judy", "Mallory", "Niaj", "Oscar", "Peggy", "Rupert", "Sybil", "Trent", "Victor", "Walter"
]

NAME_TO_GENDER = {
    "Jair": "Male", "Yahir": "Male", "Oliver": "Male", "Hiroshi": "Male", 
    "Alice": "Female", "Bob": "Male", "Charlie": "Male", "David": "Male", 
    "Eve": "Female", "Frank": "Male", "Grace": "Female", "Heidi": "Female", 
    "Ivan": "Male", "Judy": "Female", "Mallory": "Female", "Niaj": "Male", 
    "Oscar": "Male", "Peggy": "Female", "Rupert": "Male", "Sybil": "Female", 
    "Trent": "Male", "Victor": "Male", "Walter": "Male"
}

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
HOURS = [9, 10, 11, 13, 14, 15, 16] # 7 working hours range

def get_slots():
    slots = []
    for d in DAYS:
        for h in HOURS:
            slots.append(f"{d} {h}:00")
            slots.append(f"{d} {h}:30")
    return slots

ALL_SLOTS = get_slots()

def load_persona_pool():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pool_path = os.path.join(current_dir, "../../access_control/data_builder/profile/collaborative_persona_pool.json")
        
    if not os.path.exists(pool_path):
        print(f"Warning: Persona pool not found at {pool_path}")
        return None
        
    with open(pool_path, 'r') as f:
        return json.load(f)

def generate_persona_data(pool, name):
    if not pool:
        return {
            "role": "Employee",
            "authority_level": "team member",
            "background_agent": "An employee.",
            "xml_persona_entry": f"<{name}_persona>An employee.</{name}_persona>", 
            "temperament": "neutral"
        }

    # Simplified extraction from pool logic
    level = random.choice(pool['job_dimensions']['levels'])
    tenure = random.choice(pool['job_dimensions']['tenures'])
    role = random.choice(pool['job_dimensions']['roles'])
    temperament = random.choice(pool['job_dimensions']['temperaments'])
    working_style = random.choice(pool['job_dimensions']['working_styles'])
    authority_level = random.choice(pool['job_dimensions']['authority_levels'])
    
    security_behavior = random.choice(pool['job_dimensions']['security_behaviors'])

    template = pool['templates']['description_format']
    
    gender = NAME_TO_GENDER.get(name, "N/A")
    
    # Fill arbitrary values for simpler logic
    description_1st = template.format(
        age=30, gender=gender, level=level, role=role, tenure=tenure,
        temperament=temperament, working_style=working_style,
        job_responsibility="working", security_behavior=security_behavior,
        authority_level=authority_level
    )
    
    # Remove irrelevant text for meeting scheduling using regex for robustness
    # Template: "When it comes to data and access, I {security_behavior}."
    import re
    description_1st = re.sub(r" When it comes to data and access, .*?\.", "", description_1st)
    
    description_2nd = description_1st.replace("I am", "You are")
    
    formatted_xml_entry = f"<{name}_persona>\n{description_1st}\n</{name}_persona>"
    
    return {
        "role": role,
        "authority_level": authority_level,
        "background_agent": description_2nd, 
        "xml_persona_entry": formatted_xml_entry,
        "temperament": temperament
    }

def generate_scenario_complex(num_users, scenario_id_base, difficulty="random", disclosure_mode="partial"):
    if num_users > len(NAMES):
        num_users = len(NAMES)
    
    selected_names = random.sample(NAMES, num_users)
    persona_pool = load_persona_pool()
    
    # Determine scenario type
    # 1. Consensus Possible (Everyone matches on at least one preferred slot)
    # 2. Negotiation Needed (Matches only exist if some users dip into secondary slots)
    # 3. Partial Attendance (No full match, must drop optional users)
    
    if difficulty == "random":
        difficulty = random.choice(["consensus", "negotiation", "partial", "partial"]) # weight partial/negotiation slightly higher?
        
    users = []
    
    # Select "Essential" users who MUST attend
    # Adjust ratio: 30% to 70% of users should be essential to ensure difficulty
    min_ess = max(1, int(num_users * 0.3))
    max_ess = max(min_ess + 1, int(num_users * 0.7))
    num_essential = random.randint(min_ess, max_ess)
    essential_users = selected_names[:num_essential]
    
    # Ground Truth Logic
    winning_slot = None
    
    if difficulty == "consensus":
        # Pick 1 random slot that is PREFERRED by everyone
        winning_slot = random.choice(ALL_SLOTS)
    elif difficulty == "negotiation":
        # Pick 1 random slot that is SECONDARY for some, PREFERRED for others
        winning_slot = random.choice(ALL_SLOTS)
    elif difficulty == "partial":
        # Pick slot that works for ESSENTIAL only
        winning_slot = random.choice(ALL_SLOTS)
    
    # --------------------------------------------------------------------------
    # PRE-CALCULATE DISTRACTORS (Shared across users)
    # --------------------------------------------------------------------------
    num_distractors = random.randint(1, 2)
    distractor_slots = []
    candidates = [s for s in ALL_SLOTS if s != winning_slot]
    if len(candidates) >= num_distractors:
        distractor_slots = random.sample(candidates, num_distractors)
    
    # Assign blockers for each distractor
    distractor_blockers = {}
    for ds in distractor_slots:
        if essential_users:
            num_blockers = random.randint(1, min(2, len(essential_users)))
            blockers = random.sample(essential_users, num_blockers)
            distractor_blockers[ds] = set(blockers)
        else:
            distractor_blockers[ds] = set()

    user_configs = []

    for name in selected_names:
        p_data = generate_persona_data(persona_pool, name)
        is_essential = name in essential_users
        
        # Generate Slots
        preferred = set()
        secondary = set()
        
        # Add random noise slots
        noise_slots = random.sample(ALL_SLOTS, random.randint(3, 8))
        for s in noise_slots:
            if random.random() < 0.7:
                preferred.add(s)
            else:
                secondary.add(s)
        
        # Enforce Ground Truth based on difficulty
        if difficulty == "consensus":
            preferred.add(winning_slot)
        elif difficulty == "negotiation":
            # 50% chance to be preferred, 50% secondary (forcing negotiation)
            if random.random() < 0.5:
                preferred.add(winning_slot)
                if winning_slot in secondary: secondary.remove(winning_slot)
            else:
                secondary.add(winning_slot)
                if winning_slot in preferred: preferred.remove(winning_slot)
        elif difficulty == "partial":
            if is_essential:
                preferred.add(winning_slot) # Essential users can make it
            else:
                # Optional users CANNOT make it to the winning slot (creating conflict)
                if winning_slot in preferred: preferred.remove(winning_slot)
                if winning_slot in secondary: secondary.remove(winning_slot)

        # --------------------------------------------------------------------------
        # DISTRACTOR COMPLIANCE
        # --------------------------------------------------------------------------
        for ds in distractor_slots:
            is_blocker = name in distractor_blockers[ds]
            
            if is_blocker:
                 # Remove from availability
                if ds in preferred: preferred.remove(ds)
                if ds in secondary: secondary.remove(ds)
            else:
                # Promote to Preferred/Secondary (make it look tempting)
                if random.random() < 0.8:
                    preferred.add(ds)
                else:
                    secondary.add(ds)

        # Convert to lists
        preferred_list = sorted(list(preferred), key=lambda x: ALL_SLOTS.index(x))
        secondary_list = sorted(list(secondary), key=lambda x: ALL_SLOTS.index(x))
        
        # Prioritize weight/stubbornness
        # "Stubborn" users hide their secondary slots initially
        is_stubborn = random.choice([True, False])
        
        goal_text = (
            f"You are {name}, a {p_data['role']}. "
            f"Attendance Status: {'REQUIRED' if is_essential else 'OPTIONAL'}.\n"
            f"You need to schedule a meeting. "
            f"PREFERRED TIMES (High Priority): {preferred_list}. "
            f"SECONDARY TIMES (Low Priority / Emergency only): {secondary_list}. "
        )
        
        if is_stubborn:
            goal_text += (
                "\nSTRATEGY: You are busy and stubborn. "
                "Initially, ONLY offer your PREFERRED times. "
                "Do NOT reveal your secondary times unless the agent explicitly asks if you can adjust or check backup slots, "
                "or if it seems impossible to find a time otherwise."
            )
        else:
            goal_text += (
                "\nSTRATEGY: You are flexible. "
                "You can offer your preferred times first, but mention you have other slots if needed. "
                "If asked, be willing to switch to secondary times."
            )
            
        if not is_essential:
            goal_text += "\nNote: You are an optional attendee. If no time works for everyone, you can offer to skip the meeting."

        user_configs.append({
            "id": name,
            "role": p_data["role"],
            "is_essential": is_essential,
            "preferred_slots": preferred_list,
            "secondary_slots": secondary_list,
            "xml_persona_entry": p_data["xml_persona_entry"],
            "goal": goal_text,
            "is_stubborn": is_stubborn
        })

    # --- ENFORCE DIFFICULTY CONSTRAINTS ---
    # Retrieve all slots for checking
    def get_all_slots(u_conf):
        return set(u_conf['preferred_slots'] + u_conf['secondary_slots'])

    if difficulty == 'partial':
        # Constraint: NO slot should work for EVERYONE.
        # Check intersection of all users
        common_all = set(ALL_SLOTS)
        for u in user_configs:
            common_all &= get_all_slots(u)
        
        # If there are common slots, break them by removing from an OPTIONAL user
        # (We cannot remove from essential users because they MUST attend the winning slot if it exists,
        # but in 'partial', the winning slot works for Essential but NOT for at least one optional)
        if common_all:
            optional_users = [u for u in user_configs if not u['is_essential']]
            if optional_users:
                for slot in common_all:
                    # Pick a random optional user to "break" the consensus
                    victim = random.choice(optional_users)
                    if slot in victim['preferred_slots']: victim['preferred_slots'].remove(slot)
                    if slot in victim['secondary_slots']: victim['secondary_slots'].remove(slot)
                    
                    # Update their goal text to reflect the removal? 
                    # Implementation detail: The goal text is already generated. 
                    # If we simply remove it from the list, the agent won't see it in the user's mind,
                    # but the initial prompt "goal" string might be slightly stale if it listed specific times.
                    # The current goal text uses {preferred_list} check if it needs regeneration.
                    # Yes, the goal string hardcodes the list. We should regenerate the goal string.

    elif difficulty == 'negotiation':
        # Constraint: NO slot should be PREFERRED by EVERYONE.
        # (It's okay if it works for everyone, but at least one person must have it as secondary)
        common_preferred = set(ALL_SLOTS)
        for u in user_configs:
            common_preferred &= set(u['preferred_slots'])
            
        if common_preferred:
            # Force at least one user to demote this slot to secondary
            for slot in common_preferred:
                victim = random.choice(user_configs)
                if slot in victim['preferred_slots']:
                    victim['preferred_slots'].remove(slot)
                    if slot not in victim['secondary_slots']:
                        victim['secondary_slots'].append(slot)
                        # Re-sort to look nice
                        victim['secondary_slots'].sort(key=lambda x: ALL_SLOTS.index(x))

    
    # --- FINAL SAFETY CHECK ---
    # Determine the intersection of ALL essential users' availability (Preferred + Secondary)
    # This must NOT be empty, otherwise the scenario is unsolvable for "Perfect Success"
    essential_configs = [u for u in user_configs if u['is_essential']]
    if essential_configs:
         common_essential = set(ALL_SLOTS)
         for u in essential_configs:
             common_essential &= (set(u['preferred_slots']) | set(u['secondary_slots']))
             
         if not common_essential:
             # Defensive Fix: Inject a solution
             failsafe_slot = winning_slot if winning_slot else random.choice(ALL_SLOTS)
             # Force inject into essential users
             for u in essential_configs:
                 has_slot = failsafe_slot in u['preferred_slots'] or failsafe_slot in u['secondary_slots']
                 if not has_slot:
                     # Add to secondary to minimize disruption
                     u['secondary_slots'].append(failsafe_slot)
                     u['secondary_slots'].sort(key=lambda x: ALL_SLOTS.index(x))

    # Determine disclosure behavior
    proactive_ids = set()
    if disclosure_mode == 'full':
        # All users are proactive
        proactive_ids = {u['id'] for u in user_configs}
    else: # partial
        # Only some users are proactive (e.g. 40-60%)
        # Ensure at least one is silent if possible to force communication
        # But also ensure at least one is proactive so it's not dead silence
        n_proactive = random.randint(max(1, len(user_configs) // 3), max(1, len(user_configs) * 2 // 3))
        proactive_ids = set(random.sample([u['id'] for u in user_configs], n_proactive))

    # Regenerate goal texts to match the modified slots
    for u in user_configs:
        # Re-sort lists just in case
        u['preferred_slots'].sort(key=lambda x: ALL_SLOTS.index(x))
        u['secondary_slots'].sort(key=lambda x: ALL_SLOTS.index(x))
        
        goal_text = (
            f"You are {u['id']}, a {u['role']}. "
            f"Attendance Status: {'REQUIRED' if u['is_essential'] else 'OPTIONAL'}.\n"
            f"You need to schedule a meeting. "
            f"PREFERRED TIMES (High Priority): {u['preferred_slots']}. "
            f"SECONDARY TIMES (Low Priority / Emergency only): {u['secondary_slots']}. "
        )
        
        # DISCLOSURE INSTRUCTION
        if u['id'] in proactive_ids:
            goal_text += (
                "\nINITIAL BEHAVIOR: You are proactive. "
                "In your VERY FIRST message, you MUST explicitly list all your PREFERRED slots to help the agent."
            )
        else:
             goal_text += (
                "\nINITIAL BEHAVIOR: You are passive. "
                "In your VERY FIRST message, simply greet the agent (e.g., 'Hi, I'm here'). "
                "DO NOT reveal your slots immediately. Wait for the agent to ask you specifically."
            )

        if u['is_stubborn']:
            goal_text += (
                "\nNEGOTIATION STRATEGY: You are busy and stubborn. "
                "When creating your schedule or answering questions, ONLY offer your PREFERRED times initially. "
                "Do NOT reveal your secondary times unless the agent explicitly asks if you can adjust or check backup slots, "
                "or if it seems impossible to find a time otherwise."
            )
        else:
            goal_text += (
                "\nNEGOTIATION STRATEGY: You are flexible. "
                "You can offer your preferred times, but mention you have other slots if needed. "
                "If asked, be willing to switch to secondary times."
            )
            
        if not u['is_essential']:
            goal_text += "\nNote: You are an optional attendee. If no time works for everyone, you can offer to skip the meeting."
        
        u['goal'] = goal_text

    # Construct System Prompt for Agent
    user_xml_list = "\n".join([u["xml_persona_entry"] for u in user_configs])
    
    agent_prompt = f"""You are a helpful assistant facilitating multi-user collaboration for our team.

COLLABORATIVE GOAL:
Schedule a meeting for the following participants: {", ".join(selected_names)}.

YOUR MISSION:
1. Facilitate the discussion to find a meeting time that works for everyone.
2. Prioritize a time that works for EVERYONE (Preferred slots > Secondary slots).
3. Identify and resolve conflicts by negotiating or asking users to adjust their schedules.
4. Detect when a consensus is reached and finalize the schedule.

PARTICIPANT PROFILES (For context only - DO NOT roleplay these users):
{user_xml_list}

RULES:
1. You are the FACILITATOR. Do not assume the identity of any user.
2. Gather availability if it is not yet clear.
3. If conflicts arise, ask users if they can switch to secondary/backup slots.
4. If a time for ALL is impossible, you may suggest dropping OPTIONAL participants, but prioritizing REQUIRED ones.
5. Be professional, neutral, and helpful.

MESSAGE FORMAT:
User messages will be formatted as: <UserName>message content</UserName>

RESPONSE FORMAT:
You must address users directly using the following JSON format:
{{
  "target": "User Name" or "all",
  "content": "Your message here...",
  "decision": "query" or "propose"
}}

TERMINATION:
IF GOAL ACHIEVED:
If a time is agreed upon by all necessary participants, output ONLY a JSON object:
{{
  "goal_achieved": true,
  "final_schedule": "[Day Time]",
  "attendees": ["list", "of", "confirmed", "attendees"],
  "final_report": "Meeting finalized for [Day Time] with [Names]."
}}
Do NOT say anything else. Stop the conversation immediately.
"""
    
    scenario_data = {
        "id": f"meeting_{difficulty}_{scenario_id_base}",
        "scenario": "MeetingScheduling_Complex",
        "difficulty": difficulty,
        "disclosure_mode": disclosure_mode,
        "users": user_configs,
        "system_prompt": agent_prompt,
        "prompt": agent_prompt,
        "params": {
            "all_users": selected_names,
            "essential_users": essential_users,
            "optimal_solution": winning_slot,
            "proactive_users": list(proactive_ids)
        }
    }
    
    return scenario_data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count_per_setting", type=int, default=10, help="Number of scenarios per difficulty per user count")
    parser.add_argument("--output", type=str, required=True, help="Output directory or file path")
    parser.add_argument("--min_users", type=int, default=6)
    parser.add_argument("--max_users", type=int, default=6)
    parser.add_argument("--disclosure_mode", type=str, default="partial", choices=["full", "partial"], 
                        help="Mode for initial user disclosure: 'full' (everyone speaks) or 'partial' (mixed)")
    
    args = parser.parse_args()
    
    scenarios = []
    difficulties = ["consensus", "negotiation", "partial"]
    id_counter = 1000
    
    print(f"Generating meeting scenarios...")
    print(f"User range: {args.min_users} to {args.max_users}")
    print(f"Disclosure mode: {args.disclosure_mode}")
    print(f"Count per setting (per difficulty): {args.count_per_setting}")

    for n_users in range(args.min_users, args.max_users + 1):
        print(f"  Processing {n_users} users...")
        for diff in difficulties:
            for i in range(args.count_per_setting):
                scenario = generate_scenario_complex(n_users, id_counter, difficulty=diff, disclosure_mode=args.disclosure_mode)
                scenarios.append(scenario)
                id_counter += 1
        
    # Determine output path
    output_path = args.output
    if not output_path.endswith('.jsonl'):
        # Assume it's a directory
        filename = f"meeting_scheduling_disclosure_{args.disclosure_mode}_{args.min_users}_to_{args.max_users}_each_{args.count_per_setting}.jsonl"
        os.makedirs(output_path, exist_ok=True)
        output_path = os.path.join(output_path, filename)
    else:
        # It's a file path, ensure parent dir exists
        output_dir = os.path.dirname(os.path.abspath(output_path))
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            
    with open(output_path, 'w', encoding='utf-8') as f:
        for s in scenarios:
            f.write(json.dumps(s, ensure_ascii=False) + '\n')
            
    print(f"Generated {len(scenarios)} complex scenarios ({args.disclosure_mode} disclosure) to {output_path}")

if __name__ == "__main__":
    main()
