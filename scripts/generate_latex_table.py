
import os
import json
import glob
import numpy as np

# Configuration
SCENARIOS = {
    "Shared Queue": {
        "root_dir": "results/results/shared_queue",
        "metrics": {"F1_Score": "F1_Score"}, 
        "is_root_metric": False
    },
    "Instruction Following": {
        "root_dir": "results/results/multiuser_instruction_following",
        "metrics": {"avg_accuracy": "accuracy"},
        "is_root_metric": False,
        "filter_qwen": True
    },
    "Meeting Scheduling": {
        "root_dir": "results/results/meeting_scheduling",
        "metrics": {"success_rate": "success_rate"},
        "is_root_metric": False
    },
    "Access Control": {
        "root_dir": "results/results/access_control",
        "metrics": {"privacy_score": "privacy_score", "utility_score": "utility_score"},
        "is_root_metric": True
    }
}

MODEL_NAME_MAP = {
    "openai-gpt-4o-mini": "GPT-4o-mini",
    "openai-gpt-5-nano": "GPT-5-Nano",
    "openai-gpt-5.2": "GPT-5.2",
    "anthropic-claude-sonnet-4.5": "Claude-Sonnet-4.5",
    "google-gemini-3-pro-preview": "Gemini-3-Pro",
    "anthropic-claude-3-5-sonnet": "Claude-3.5-Sonnet",
    "anthropic-claude-haiku-4.5": "Claude-Haiku-4.5",
    "anthropic-claude-3.5-haiku": "Claude-3.5-Haiku",
    "google-gemini-3-flash-preview": "Gemini-3-Flash",
    "google-gemini-2.5-flash": "Gemini-2.5-Flash",
    "x-ai-grok-4.1-fast": "Grok-4.1-Fast",
    "x-ai-grok-3-mini": "Grok-3-Mini",
    "deepseek-deepseek-r1-0528": "DeepSeek-R1",
    "meta-llama-llama-3-70b-instruct": "Llama-3-70B",
    "meta-llama-llama-3-8b-instruct": "Llama-3-8B",
    "qwen-qwen3-30b-a3b": "Qwen3-30B",
    "qwen-qwen3-4b-instruct-2507": "Qwen3-4B-IT",
    "z-ai-glm-4.5-air": "GLM-4.5-Air",
    "openai-gpt-oss-120b": "GPT-OSS-120B"
}

# Categorization: True = Proprietary, False = Open-Weights
PROPRIETARY_MODELS = {
    "GPT-4o-mini", "GPT-5-Nano", "GPT-5.1", "GPT-5.2",
    "Claude-3.5-Sonnet", "Claude-Haiku-4.5", "Claude-3.5-Haiku", "Claude-Sonnet-4.5",
    "Gemini-3-Flash", "Gemini-2.5-Flash", "Gemini-3-Pro",
    "Grok-4.1-Fast", "Grok-3-Mini",
    "GLM-4.5-Air" 
}
# Remaining in MODEL_NAME_MAP will be assumed Open-Weights if not in this set

def is_finetuned_artifact(name):
    keywords = ["multiuser", "mix", "lora", "clean", "full", "epoch", "checkpoint"]
    name_lower = name.lower()
    for k in keywords:
        if k in name_lower:
            return True
    return False

def clean_model_name(dir_name):
    name = dir_name.lower().replace("/", "-")
    if name in MODEL_NAME_MAP:
        return MODEL_NAME_MAP[name]
    for v in MODEL_NAME_MAP.values():
        if v.lower() == name:
            return v
    for k, v in MODEL_NAME_MAP.items():
        if k in name:
            return v
    return dir_name 

def get_stats(values):
    if not values:
        return 0.0, 0.0
    mean = np.mean(values)
    sem = np.std(values, ddof=1) / np.sqrt(len(values)) if len(values) > 1 else 0.0
    return mean, sem

def process_scenario(name, config):
    aggregated_data = {} 
    
    root_dir = config["root_dir"]
    if not os.path.exists(root_dir):
        print(f"Warning: Root path not found {root_dir}")
        return {}
    
    dataset_paths = glob.glob(os.path.join(root_dir, "*"))
    
    for ds_path in dataset_paths:
        if not os.path.isdir(ds_path):
            continue
            
        model_paths = glob.glob(os.path.join(ds_path, "*"))
        
        for model_dir in model_paths:
            if not os.path.isdir(model_dir):
                continue
                
            model_name_raw = os.path.basename(model_dir)
            
            if "qwen3-4b-base" in model_name_raw.lower():
                continue
            if is_finetuned_artifact(model_name_raw):
                continue
            if "cdbee" in model_name_raw:
                continue
                
            display_name = clean_model_name(model_name_raw)
            if display_name not in aggregated_data:
                aggregated_data[display_name] = {m: [] for m in config["metrics"].values()}
            
            jsonl_files = glob.glob(os.path.join(model_dir, "results*.jsonl"))
            if not jsonl_files:
                continue
            jsonl_files.sort(key=os.path.getmtime, reverse=True)
            target_file = jsonl_files[0]
            
            try:
                with open(target_file, 'r') as f:
                    for line in f:
                        try:
                            item = json.loads(line)
                            if "error" in item:
                                continue
                            if "per_turn_metrics" in item and len(item["per_turn_metrics"]) == 0:
                                continue
                            
                            source = item
                            if not config["is_root_metric"]:
                                source = item.get("metrics", {})
                                
                            if not source:
                                continue
                                
                            for metric_disp, metric_key in config["metrics"].items():
                                val = source.get(metric_key)
                                if val is not None:
                                    try:
                                        aggregated_data[display_name][metric_key].append(float(val))
                                    except:
                                        pass
                        except:
                            continue
            except Exception as e:
                pass

    final_results = {} 
    for model, metrics_map in aggregated_data.items():
        stats_map = {}
        has_data = False
        for metric_disp, metric_key in config["metrics"].items():
            vals = metrics_map[metric_key]
            if vals:
                mean, sem = get_stats(vals)
                stats_map[metric_disp] = (mean, sem)
                has_data = True
            else:
                stats_map[metric_disp] = (0.0, 0.0)
        
        if has_data:
            final_results[model] = stats_map
            
    return final_results

def quote_latex(s):
    return s.replace("_", "\\_")

def format_cell(mean, sem, is_best=False, is_second=False):
    # Check if value is logically 0 or close to it with no sem
    if mean == 0 and sem == 0:
        val_str = "0.0_{\\pm 0.0}"
    else:
        val_str = f"{mean*100:.1f}_{{\\pm {sem*100:.1f}}}"
        
    if is_best:
        return f"$\\boldsymbol{{{val_str}}}$"
    elif is_second:
        return f"\\underline{{${val_str}$}}"
    else:
        return f"${val_str}$"

def generate_table():
    data = {}
    all_models = set()
    
    # 1. Collect Data
    for scenario, config in SCENARIOS.items():
        print(f"Processing {scenario}...")
        scen_data = process_scenario(scenario, config)
        data[scenario] = scen_data
        all_models.update(scen_data.keys())
        
    sorted_models = sorted(list(all_models))
    
    # 2. Calculate Averages and Identify Max/Second Max per column
    # Columns: Queue(F1), Instruct(Acc), Priv, Util, Meeting(Succ), AVG
    
    model_averages = {} # model -> avg
    column_values = {
        "Queue": {}, "Instruct": {}, "Priv": {}, "Util": {}, "Meeting": {}, "Avg": {}
    }
    
    for model in sorted_models:
        vals = []
        
        # Queue
        q_stats = data["Shared Queue"].get(model, {}).get("F1_Score", (0,0))
        column_values["Queue"][model] = q_stats[0]
        vals.append(q_stats[0])
        
        # Instruct
        i_stats = data["Instruction Following"].get(model, {}).get("avg_accuracy", (0,0))
        column_values["Instruct"][model] = i_stats[0]
        vals.append(i_stats[0])
        
        # Priv
        p_stats = data["Access Control"].get(model, {}).get("privacy_score", (0,0))
        column_values["Priv"][model] = p_stats[0]
        vals.append(p_stats[0])
        
        # Util
        u_stats = data["Access Control"].get(model, {}).get("utility_score", (0,0))
        column_values["Util"][model] = u_stats[0]
        vals.append(u_stats[0])
        
        # Meeting
        m_stats = data["Meeting Scheduling"].get(model, {}).get("success_rate", (0,0))
        column_values["Meeting"][model] = m_stats[0]
        vals.append(m_stats[0])
        
        # Avg
        avg = np.mean(vals) if vals else 0
        model_averages[model] = avg
        column_values["Avg"][model] = avg

    # Determine Best/Second Best per column
    best_second_map = {col: {"best": -1, "second": -1} for col in column_values}
    
    for col, val_map in column_values.items():
        sorted_vals = sorted(list(set(val_map.values())), reverse=True)
        if len(sorted_vals) > 0:
            best_second_map[col]["best"] = sorted_vals[0]
        if len(sorted_vals) > 1:
            best_second_map[col]["second"] = sorted_vals[1]

    def get_fmt(model, col_name, explicit_stats=None):
        val = column_values[col_name].get(model, 0)
        
        if explicit_stats:
            mean, sem = explicit_stats
        else:
            mean = val
            sem = 0
            
        is_best = (val == best_second_map[col_name]["best"]) and (val > 0)
        is_second = (val == best_second_map[col_name]["second"]) and (val > 0)
        
        return format_cell(mean, sem, is_best, is_second)

    # 3. Categorize
    prop_list = [m for m in sorted_models if m in PROPRIETARY_MODELS]
    open_list = [m for m in sorted_models if m not in PROPRIETARY_MODELS]
    
    # 4. Generate LaTeX
    out = []
    out.append("\\begin{table*}[t]")
    out.append("\\centering")
    out.append("\\small")
    # Columns: Model, Queue, Instruct, Priv, Util, Meeting, Avg
    out.append("\\begin{tabular}{lcccccc}")
    out.append("\\toprule")
    
    # Header Row 1
    # Note: Using user requested widths and order: Instruct, Access, Meeting
    out.append("\\multirow{2}{*}{\\textbf{Model}} "
               "& \\multicolumn{2}{>{\\centering\\arraybackslash}p{3.2cm}}{\\textbf{Multi-user Instruction Following}} "
               "& \\multicolumn{2}{>{\\centering\\arraybackslash}p{3.2cm}}{\\textbf{Cross-user Access Control}} "
               "& \\multicolumn{1}{>{\\centering\\arraybackslash}p{2.8cm}}{\\textbf{Multi-user Meeting Coordination}} "
               "& \\multirow{2}{*}{\\textbf{Avg}} \\\\")
    
    # Header Row 2 lines
    # Instruct (cols 2-3), Access (cols 4-5), Meeting (col 6)
    out.append("\\cmidrule(lr){2-3} \\cmidrule(lr){4-5} \\cmidrule(lr){6-6}")
    
    # Header Row 3 content
    out.append("& Queue ($F_1$) & Instruct (Acc.) & Privacy & Utility & Success Rate & \\\\")
    
    # Proprietary Block
    out.append("\\midrule")
    out.append("\\multicolumn{7}{l}{\\textit{\\textbf{Proprietary Models}}} \\\\")
    out.append("\\midrule")
    
    for model in prop_list:
        row = [f"\\textbf{{{quote_latex(model)}}}"]
        row.append(get_fmt(model, "Queue", data["Shared Queue"].get(model, {}).get("F1_Score")))
        row.append(get_fmt(model, "Instruct", data["Instruction Following"].get(model, {}).get("avg_accuracy")))
        row.append(get_fmt(model, "Priv", data["Access Control"].get(model, {}).get("privacy_score")))
        row.append(get_fmt(model, "Util", data["Access Control"].get(model, {}).get("utility_score")))
        row.append(get_fmt(model, "Meeting", data["Meeting Scheduling"].get(model, {}).get("success_rate")))
        row.append(get_fmt(model, "Avg"))
        out.append(" & ".join(row) + " \\\\")

    # Open Block
    out.append("\\midrule")
    out.append("\\multicolumn{7}{l}{\\textit{\\textbf{Open-Weights Models}}} \\\\")
    out.append("\\midrule")

    for model in open_list:
        row = [f"\\textbf{{{quote_latex(model)}}}"]
        row.append(get_fmt(model, "Queue", data["Shared Queue"].get(model, {}).get("F1_Score")))
        row.append(get_fmt(model, "Instruct", data["Instruction Following"].get(model, {}).get("avg_accuracy")))
        row.append(get_fmt(model, "Priv", data["Access Control"].get(model, {}).get("privacy_score")))
        row.append(get_fmt(model, "Util", data["Access Control"].get(model, {}).get("utility_score")))
        row.append(get_fmt(model, "Meeting", data["Meeting Scheduling"].get(model, {}).get("success_rate")))
        row.append(get_fmt(model, "Avg"))
        out.append(" & ".join(row) + " \\\\")
        
    out.append("\\bottomrule")
    out.append("\\end{tabular}")
    out.append("\\caption{Performance of various models across Muses-Bench scenarios. Metrics shown are Mean $\\pm$ Standard Error. The best performance is \\textbf{bolded} and the second best is \\underline{underlined}.}")
    out.append("\\label{tab:main_results}")
    out.append("\\end{table*}")
    
    final_latex = "\n".join(out)
    print(final_latex)
    
    with open("results_table.tex", "w") as f:
        f.write(final_latex)

if __name__ == "__main__":
    generate_table()
