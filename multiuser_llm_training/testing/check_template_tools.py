
from transformers import AutoTokenizer

MODEL_NAME = "Qwen/Qwen3-4B-Base"

def main():
    print(f"Loading tokenizer for {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    
    # Define a conversation with tool calling flow
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the weather in New York?"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"location": "New York, NY"}'
                    }
                }
            ]
        },
        {
            "role": "tool",
            "name": "get_weather",
            "content": '{"temperature": 72, "condition": "Sunny"}'
        },
        {
            "role": "assistant",
            "content": "The weather in New York is currently 72 degrees and sunny."
        }
    ]
    
    print("\n========== Testing Tool Call Rendering ==========")
    try:
        rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        print(f"--- Rendered String ---\n{rendered}")
    except Exception as e:
        print(f"Error applying chat template: {e}")

if __name__ == "__main__":
    main()
