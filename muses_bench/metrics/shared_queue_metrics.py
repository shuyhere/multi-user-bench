"""Shared LLM Inference Queue Evaluation Metrics."""

from typing import Dict, List, Any, Set

def evaluate_shared_queue(
    model_output: Dict[str, Any],
    ground_truth: Dict[str, Any],
    resources: Dict[str, Any] = None
) -> Dict:
    """
    Evaluates the Shared LLM Inference Queue scenario.

    Metrics:
    1. MAIS (Maximal Applicable Instruction Score):
       Recall of correctly accepted instructions.
       MAIS = |Model_Accepted INTERSECT GT_Accepted| / |GT_Accepted|
    
    Args:
        model_output: Dict containing:
            - accepted_instructions: List[str] (ids)
        ground_truth: Dict containing:
            - accepted_instructions: List[str]
        resources: Dict (unused but kept for compatibility)

    Returns:
        Dict of scores.
    """
    
    # --- 1. MAIS Calculation ---
    gt_accepted = set(ground_truth.get("accepted_instructions", []))
    model_accepted = set(model_output.get("accepted_instructions", []))
    
    if not gt_accepted:
        # If no instructions should be accepted, and model accepted None -> 1.0
        # If model accepted some -> 0.0?
        mais = 1.0 if not model_accepted else 0.0
    else:
        # Intersection
        correct_accepted = model_accepted.intersection(gt_accepted)
        mais = len(correct_accepted) / len(gt_accepted)
        
    # --- 2. Accuracy Calculation ---
    # User Request: "Accept what should be accepted, reject what should be rejected, then calculate average accuracy"
    
    # 2.1 Identify Universe of Instructions (from Ground Truth)
    gt_rejected_raw = ground_truth.get("rejected_instructions", [])
    gt_rejected = set()
    for item in gt_rejected_raw:
        if isinstance(item, dict):
            gt_rejected.add(item.get("id"))
        else:
            gt_rejected.add(item)
            
    all_instructions = gt_accepted.union(gt_rejected)
    total_instructions = len(all_instructions)
    
    # 2.2 Calculate Correct Decisions
    # For each instruction in the universe:
    # - It is a CORRECT decision if:
    #   a) It is in GT_Accepted AND it is in Model_Accepted (True Positive)
    #   b) It is in GT_Rejected AND it is NOT in Model_Accepted (True Negative)
    #      (We assume implicit rejection: if not in accepted list, it is rejected)
    
    correct_decisions = 0
    
    for instr_id in all_instructions:
        in_gt_accept = instr_id in gt_accepted
        in_model_accept = instr_id in model_accepted
        
        if in_gt_accept and in_model_accept:
            correct_decisions += 1  # True Positive
        elif (not in_gt_accept) and (not in_model_accept):
            correct_decisions += 1  # True Negative
            
    accuracy = correct_decisions / total_instructions if total_instructions > 0 else 0.0

    # --- 3. F1 Score Calculation ---
    # TP: Correctly Accepted (in Model AND in GT)
    # FP: Incorrectly Accepted (in Model but NOT in GT)
    # FN: Incorrectly Rejected (in GT but NOT in Model) - i.e., Missed Accepted
    
    tp = len(correct_accepted) if gt_accepted else 0
    fp = len(model_accepted - gt_accepted)
    fn = len(gt_accepted - model_accepted)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0  # Recall should be identical to MAIS
    
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "MAIS": mais,
        "Accuracy": accuracy,
        "F1_Score": f1_score,
        "Precision": precision,
        "Recall": recall,
        "gt_accepted_count": len(gt_accepted),
        "model_accepted_count": len(model_accepted),
        "correct_accepted_count": len(correct_accepted) if gt_accepted else 0,
        "total_instructions": total_instructions,
        "correct_decisions": correct_decisions
    }

def print_shared_queue_summary(metrics: Dict, verbose: bool = True):
    print("\n[SHARED QUEUE EVALUATION]")
    print(f"  F1 Score: {metrics['F1_Score']:.2%}")
    print(f"  Accuracy: {metrics['Accuracy']:.2%}")
    print(f"  MAIS:     {metrics['MAIS']:.2%}")
    if verbose:
        print(f"  Precision: {metrics['Precision']:.2%}")
        print(f"  Recall:    {metrics['Recall']:.2%}")
        print(f"  Decisions: {metrics['correct_decisions']}/{metrics['total_instructions']} Correct")
        print(f"  Accepted:  {metrics['correct_accepted_count']}/{metrics['gt_accepted_count']} Correctly Accepted")
