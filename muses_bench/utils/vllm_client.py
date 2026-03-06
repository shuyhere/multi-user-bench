import torch
import os
import gc
# Lazy import vllm
try:
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest
    from vllm.distributed import destroy_distributed_environment, destroy_model_parallel
except ImportError:
    LLM = None
    SamplingParams = None
    LoRARequest = None

def load_vllm_model(
    model_name_or_path: str,
    lora_path: str | None = None,
    lora_name: str = "default_lora",
) -> tuple[LLM, LoRARequest | None]:
    """
    Load an LLM and its associated LoRA model if applicable.
    
    Args:
        model_name_or_path: Path or name of the base model
        lora_path: Path to the LoRA adapter (optional)
        lora_name: Name for the LoRA adapter
        
    Returns:
        tuple: (LLM client, LoRARequest or None)
    """
    if LLM is None:
        raise ImportError("vLLM is not installed or failed to import.")
    
    load_kwargs = dict(
        model=model_name_or_path,
        trust_remote_code=True,
        enable_prefix_caching=True,
        enable_lora=False,
        tensor_parallel_size=torch.cuda.device_count(),
        max_num_seqs=32,
        gpu_memory_utilization=0.82,
        max_model_len=32768,
        enforce_eager=True, 
    )

    if "phi-moe" in model_name_or_path:
        load_kwargs["enforce_eager"] = True
    
    # Check for mistral specific configs (kept from previous vllm_helper just in case, but inference.py doesn't have them)
    # inference.py just uses defaults. I will stick to inference.py as requested but keep enforce_eager=True as default there

    lora_request = None
    if lora_path is not None:
        if os.path.exists(lora_path):
            print(f"Loading LoRA from {lora_path}")
            load_kwargs["enable_lora"] = True
            load_kwargs["max_lora_rank"] = 64
            # load_kwargs["enable_lora_bias"] = True 
            lora_request = LoRARequest(
                lora_name=lora_name,
                lora_int_id=1,
                lora_path=lora_path,
            )
        else:
            print(f"Warning: LoRA path {lora_path} does not exist. Loading base model only.")

    llm_client = LLM(**load_kwargs)
    return llm_client, lora_request

def generate_vllm_response(
    llm: LLM,
    lora_request: LoRARequest | None,
    messages: list[dict[str, str]],
    top_p: float = 1.0,
    max_tokens: int = 32768,
    temperature: float = 1.0,
    stop: list[str] = [],
    min_tokens: int = 1,
):
    """
    Generate response for a single conversation using vLLM.
    Adapting from inference.py prompt_llm but dealing with single conversation to match current usage.
    """
    tokenizer = llm.get_tokenizer()

    # Get the EOS token string
    if hasattr(tokenizer, "eos_token") and tokenizer.eos_token is not None:
        eos_token_str = tokenizer.eos_token
    else:
        try:
            eos_token_str = tokenizer.decode([tokenizer.eos_token_id])
        except:
            eos_token_str = ""

    sampling_params = SamplingParams(
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        skip_special_tokens=True,
        stop=[eos_token_str] + stop if eos_token_str else stop,
        stop_token_ids=[151645],
        min_tokens=min_tokens,
        repetition_penalty=1.1, # Added from inference.py
    )

    # Format prompt
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    if isinstance(text, list):
         text = tokenizer.decode(text)

    generate_kwargs = {
        "prompts": [text],
        "sampling_params": sampling_params,
        "use_tqdm": True,
        "lora_request": lora_request,
    }

    completions = llm.generate(**generate_kwargs)
    response = completions[0].outputs[0].text
    return response

def cleanup_vllm(llm_client):
    # Basic cleanup
    if hasattr(llm_client, "llm_engine"):
        del llm_client.llm_engine
    
    try:
        destroy_model_parallel()
    except:
        pass
    try:
        destroy_distributed_environment()
    except:
        pass
        
    gc.collect()
    torch.cuda.empty_cache()
