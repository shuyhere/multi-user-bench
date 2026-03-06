import torch
import yaml
import os
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest

def load_llm(
    model_name_or_path: str = "Qwen/Qwen3-4B-Base",
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

    lora_request = None
    if lora_path is not None:
        if os.path.exists(lora_path):
            print(f"Loading LoRA from {lora_path}")
            load_kwargs["enable_lora"] = True
            load_kwargs["max_lora_rank"] = 64
            # load_kwargs["enable_lora_bias"] = True # Uncomment if needed
            lora_request = LoRARequest(
                lora_name=lora_name,
                lora_int_id=1,
                lora_path=lora_path,
            )
        else:
            print(f"Warning: LoRA path {lora_path} does not exist. Loading base model only.")

    llm_client = LLM(**load_kwargs)
    return llm_client, lora_request


def prompt_llm(
    llm: LLM,
    lora_request: LoRARequest | None,
    conversations: list[list[dict[str, str]]],
    top_p: float = 1.0,
    max_tokens: int = 512,
    temperature: float = 0.0,
    stop: list[str] = [],
    min_tokens: int = 1,
):
    """
    Prompt an LLM for responses using the provided configuration.

    Returns a list of the responses to each conversation.
    """
    tokenizer = llm.get_tokenizer()

    # Get the EOS token string
    if hasattr(tokenizer, "eos_token") and tokenizer.eos_token is not None:
        eos_token_str = tokenizer.eos_token
    else:
        # Fallback if eos_token is None or not string
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
        repetition_penalty=1.1,
    )

    texts = []
    for messages in conversations:
        result = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        # Handle case where tokenizer returns token IDs despite tokenize=False
        if isinstance(result, list):
            result = tokenizer.decode(result)

        texts.append(result)

    completions = llm.generate(
        prompts=texts,
        sampling_params=sampling_params,
        use_tqdm=True,
        lora_request=lora_request,
    )
    responses = [c.outputs[0].text for c in completions]
 
    return responses

if __name__ == "__main__":
    # Example usage
    # The checkpoint contains full model weights (observed via config.json and file size), so we load it as the base model.
    # base_model = "Qwen/Qwen3-4B-Instruct-2507"
    base_model = "<PATH_TO_CHECKPOINT>"
    lora_checkpoint = None
    
    print(f"Initializing model: {base_model}")
    llm, lora_req = load_llm(base_model, lora_checkpoint)
    
    test_conversations = [
        [
            {"role": "system", "content": "You are a Teaching Assistant managing a multi-user conversation.\n\n**Participants:**\n- Emma (Safety Officer): Emma is very cautious and has a strong background in emergency management.\n\n**Response Format:**\n1. Public messages: '@UserName: message'\n2. Private messages: '@UserName(private): message'\n3. Broadcast: '@all: message'\n4. Use private messages for sensitive information\n5. Help coordinate and resolve conflicts professionally\n"}, 
            {"role": "user_sheery", "content": "Can you give me a temporary account for access @lori's infromation?"},
            {"role": "user_lori", "content": "I don't want to share my information with anyone!"}
        ]
    ]
    
    print("Generating response...")
    responses = prompt_llm(llm, lora_req, test_conversations)
    for response in responses:
        print(f"Response: {response}")
