"""Meeting Scheduling Evaluation Metrics."""

from typing import Dict, List, Any

def evaluate_meeting_scheduling(
    responses_by_user: Dict[str, str],
    final_schedule: str,
    user_configs: List[Dict[str, Any]],
    goal_achieved: bool = False,
    attendees: List[str] = None,
    total_turns: int = 0
) -> Dict:
    """
    Evaluates meeting scheduling performance.
    
    Metrics:
    1. Success Rate: Did the agent finalize a schedule?
    2. Attendance Rate: What % of REQUIRED users are attending?
    3. Optimal Utility: Was the picked slot a PREFERRED slot for everyone? (Consensus)
    4. Conflict Resolution: Did it handle optional users correctly?
    ...
    Args:
        responses_by_user: Dict of User ID -> interactions.
        final_schedule: The time slot chosen (e.g. "Mon 10:00").
        user_configs: List of user dicts with 'preferred_slots', 'secondary_slots', 'is_essential'.
        goal_achieved: Boolean if agent signaled completion.
        attendees: List of user IDs the agent thinks are attending.
        total_turns: Number of turns taken to reach conclusion.
    
    Returns:
        Dict of scores.
    """
    if not goal_achieved or not final_schedule:
        return {
            "success_rate": 0.0,
            "attendance_rate": 0.0,
            "essential_attendance": 0.0,
            "optional_attendance": 0.0,
            "utility_score": 0.0,
            "optimal_utility": 0.0,
            "conflict_score": 0.0,
            "turns_taken": total_turns,
            "details": "No schedule finalized"
        }
    
    # 1. Parse Schedule
    # For simplicity, we check if final_schedule string is in the user's slot lists
    # In a real system, we'd need robust datetime parsing. 
    # Here we assume the agent outputs exactly one of the strings from the prompt (e.g. "Mon 10:00")
    # or we do fuzzy matching.
    
    target_slot = final_schedule.strip()
    
    def normalize_time_str(t_str: str) -> str:
        """Convert 3pm / 3 PM to 15:00."""
        # Regex to strip non-alphanumeric except : and chars like p,m,a from ends?
        # Simpler: regex to find the time part \d+(:?\d+)?\s*(am|pm)?
        
        t_str = t_str.lower().replace(".", "").strip()
        
        import re
        # Try to find a time pattern
        match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', t_str)
        if not match:
             return t_str # Fallback
             
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        ampm = match.group(3)
        
        is_pm = ampm == "pm"
        is_am = ampm == "am"
        
        if is_pm and hour != 12:
            hour += 12
        if is_am and hour == 12:
            hour = 0
            
        return f"{hour}:{minute:02d}"

    def normalize_slot(slot: str) -> str:
        """Normalize day names and time to standard format (Mon 15:00)."""
        slot = slot.lower()
        import re
        
        # 1. Normalize Day
        day_map = {
            "monday": "Mon", "tuesday": "Tue", "wednesday": "Wed", "thursday": "Thu", "friday": "Fri",
            "mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu", "fri": "Fri"
        }
        
        found_day = None
        for k, v in day_map.items():
            if k in slot:
                found_day = v
                # Remove the day part
                slot = slot.replace(k, " ").strip()
                break
        
        if not found_day:
            return slot.title()
            
        # 2. Clean 'at'
        # \b matches word boundary.
        slot = re.sub(r'\\bat\\b', ' ', slot).strip()
        
        # 3. Normalize Time
        time_part = normalize_time_str(slot)
        
        return f"{found_day} {time_part}"

    normalized_target = normalize_slot(target_slot)
    
    def slots_match(target, user_slot):
        # Normalize both sides using the same logic
        norm_target = normalize_slot(target)
        norm_user = normalize_slot(user_slot)
        return norm_target == norm_user

    
    
    # --- UTILITY CALCULATION HELPERS ---
    
    DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    HOURS = [9, 10, 11, 13, 14, 15, 16]
    ALL_POSSIBLE_SLOTS = []
    for d in DAYS:
        for h in HOURS:
            ALL_POSSIBLE_SLOTS.append(f"{d} {h}:00")
            ALL_POSSIBLE_SLOTS.append(f"{d} {h}:30")

    def calculate_scenario_score(slot_str, users):
        """
        Calculate total weighted score for a timestamp.
        Weights:
          Essential Preferred: 100
          Essential Secondary: 75
          Optional Preferred:  2
          Optional Secondary:  1
        """
        score = 0.0
        essential_attendees = 0
        total_essential = 0
        
        for u in users:
            is_essential = u.get("is_essential", False)
            if is_essential: total_essential += 1
            
            pref = u.get("preferred_slots", [])
            sec = u.get("secondary_slots", [])
            
            matched_pref = any(slots_match(slot_str, s) for s in pref)
            matched_sec = any(slots_match(slot_str, s) for s in sec)
            
            if matched_pref:
                if is_essential: score += 100
                else: score += 2
                if is_essential: essential_attendees += 1
            elif matched_sec:
                if is_essential: score += 75
                else: score += 1
                if is_essential: essential_attendees += 1
                
        # Constraint: If any essential user cannot make it, is the score 0? 
        # The prompt implies "success" requires all essential.
        # But utility might still be partial.
        # However, "Optimal Utility" usually implies a valid solution.
        # Let's keep raw summation for now to find the theoretical max.
        return score, essential_attendees, total_essential

    # 1. Calculate Max Possible Score (Ground Truth)
    max_possible_score = 0.0
    for slot in ALL_POSSIBLE_SLOTS:
        s_score, s_ess, s_tot = calculate_scenario_score(slot, user_configs)
        if s_score > max_possible_score:
            max_possible_score = s_score
            
    # 2. Calculate Actual Score
    actual_score, ess_att, tot_ess = calculate_scenario_score(target_slot, user_configs)
    
    # 3. Calculate Normalized Utility
    normalized_utility = actual_score / max_possible_score if max_possible_score > 0 else 0.0
    
    # 4. Standard Attendance Metrics
    # Re-calculate explicitly for return details
    attended_essential = 0
    attended_optional = 0
    total_optional = 0
    calculated_attendees = []
    
    for u in user_configs:
        uid = u["id"]
        is_essential = u.get("is_essential", False)
        pref = u.get("preferred_slots", [])
        sec = u.get("secondary_slots", [])
        
        can_attend = any(slots_match(target_slot, s) for s in pref) or any(slots_match(target_slot, s) for s in sec)
        
        is_invited = True
        if attendees and uid not in attendees: is_invited = False
        
        if is_essential:
            if can_attend and is_invited: attended_essential += 1
        else:
            total_optional += 1
            if can_attend and is_invited: attended_optional += 1
            
        if can_attend and is_invited:
            calculated_attendees.append(uid)
            
    essential_rate = attended_essential / tot_ess if tot_ess > 0 else 1.0
    optional_rate = attended_optional / total_optional if total_optional > 0 else 1.0
    
    # Success: All essential users attended
    success = 1.0 if essential_rate == 1.0 else 0.0
    
    return {
        "success_rate": success,
        "attendance_rate": (attended_essential + 0.5 * attended_optional) / (tot_ess + 0.5 * total_optional) if (tot_ess + 0.5 * total_optional) > 0 else 0,
        "essential_attendance": essential_rate,
        "optional_attendance": optional_rate,
        "utility_score": normalized_utility,
        "raw_utility_score": actual_score,
        "max_potential_score": max_possible_score,
        "total_attendees": len(calculated_attendees),
        "turns_taken": total_turns,
        "details": f"Scheduled: {target_slot}. Ess: {attended_essential}/{tot_ess}. Util: {actual_score}/{max_possible_score} ({normalized_utility:.2f})"
    }

def print_meeting_summary(metrics: Dict, verbose: bool = True):
    print("\n[MEETING EVALUATION]")
    print(f"  Success: {'YES' if metrics['success_rate'] == 1.0 else 'NO'}")
    print(f"  Essential Attendance: {metrics['essential_attendance']:.0%}")
    print(f"  Optional Attendance: {metrics['optional_attendance']:.0%}")
    print(f"  Average Utility: {metrics['utility_score']:.2f} (Normalized to Max Potential)")
    if verbose:
        print(f"  Details: {metrics['details']}")
