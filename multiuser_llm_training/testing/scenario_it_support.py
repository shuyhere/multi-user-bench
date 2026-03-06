import torch
import json
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = "Qwen/Qwen3-4B-Base"

# IT Support Scenario
SCENARIO = {
    "resource_name": "Corporate IT Support System",
    "all_users": [
        {
            "id": "Alice", 
            "role": "Marketing Manager", 
            "background": "Alice is 35, Female, a Marketing Manager with 4 years at the company. Alice is organized and detail-oriented. Alice's main responsibilities include managing digital marketing campaigns. Alice has basic technical knowledge but relies on IT support for network issues."
        },
        {
            "id": "Bob", 
            "role": "Finance Director", 
            "background": "Bob is 42, Male, a Finance Director with 8 years at the company. Bob is cautious and security-conscious. Bob's main responsibilities include overseeing financial reporting and budget planning. Bob frequently needs access to sensitive financial databases and is very concerned about data security."
        },
        {
            "id": "Carol", 
            "role": "Sales Representative", 
            "background": "Carol is 29, Female, a Sales Representative with 2 years at the company. Carol is friendly and communicative. Carol's main responsibilities include client relationship management. Carol works remotely and depends heavily on stable VPN and cloud access."
        }
    ],
    "conversation_history": [
        {"role": "user_Alice", "content": "我的VPN连接不上了，怎么办？"},
        {"role": "user_Bob", "content": "我需要访问财务数据库的权限"},
        {"role": "user_Carol", "content": "大家最近系统慢不慢？"}
    ]
}

def generate(model, tokenizer, prompt, max_new_tokens=512):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    stop_token_ids = [tokenizer.eos_token_id]
    if "<|im_end|>" in tokenizer.get_vocab():
        stop_token_ids.append(tokenizer.convert_tokens_to_ids("<|im_end|>"))

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,          
            temperature=0.7,
            top_p=0.8,
            repetition_penalty=1.1,
            eos_token_id=stop_token_ids,
            pad_token_id=tokenizer.eos_token_id,
        )
    
    text = tokenizer.decode(out[0], skip_special_tokens=True) 
    return text

def build_prompt(scenario):
    # 1. Basic Context
    resource = scenario.get('resource_name', 'the resource')
    prompt = (
        f"You are a helpful IT Support Assistant managing the {resource}.\n"
        "Your goal is to help users with technical issues while maintaining security and privacy.\n"
        "To address a specific user, you MUST start your message with '@UserName: ' or '@UserName(private): '.\n"
        "If you do not address a specific user with '@', your message will be considered a broadcast to everyone.\n\n"
    )
    
    # 2. User Profiles
    prompt += "PARTICIPANTS:\n"
    for user in scenario.get('all_users', []):
        uid = user['id']
        role = user['role']
        bg = user.get('background', '')
        prompt += f"- {uid} ({role}): {bg}\n"
        
    # 3. Message Rules
    prompt += (
        "\nRESPONSE RULES:\n"
        "1. To send a PUBLIC message (visible to all users): Use '@UserName: your message'\n"
        "   Example: '@Alice: Please try restarting your VPN client.'\n"
        "2. To send a PRIVATE message (visible only to that user): Use '@UserName(private): your message'\n"
        "   Example: '@Bob(private): Your database access request has been approved. Password sent to your email.'\n"
        "3. You can use '@all: ...' to address all users in a public broadcast.\n"
        "4. If replying to multiple specific users publicly, address them in separate paragraphs.\n"
        "5. Do NOT use JSON format. Use natural language.\n"
        "6. Prioritize answering their queries naturally while respecting privacy when needed.\n"
        "7. Use private messages for sensitive information (passwords, permissions, personal data).\n"
    )
    
    # 4. Conversation History
    prompt += "\nCONVERSATION:\n"
    for msg in scenario.get('conversation_history', []):
        role = msg['role']
        content = msg['content']
        if role.startswith('user_'):
            username = role.replace('user_', '')
            prompt += f"[User_{username}]: {content}\n"
        else:
            prompt += f"[{role}]: {content}\n"
    
    prompt += "\n[Agent]: "
    
    return prompt

def main():
    print(f"Loading {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    model.eval()

    # Patch Template
    current_template = tokenizer.chat_template
    if current_template:
        patch_template = current_template.replace(
            'message.role == "user"', 
            'message.role.startswith("user")'
        ).replace(
            "message.role == 'user'", 
            "message.role.startswith('user')"
        )
        tokenizer.chat_template = patch_template
        print("Chat template patched.")
    else:
        print("No default chat template found.")

    # Use IT Support Scenario
    scenario = SCENARIO
    
    system_prompt = build_prompt(scenario)
    
    print("\n========== IT Support Scenario =========")
    print(system_prompt)
    
    # For chat template
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(scenario['conversation_history'])

    prompt_str = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    print("\n========== Model Generation ==========")
    output = generate(model, tokenizer, prompt_str)
    print(output)

if __name__ == "__main__":
    main()
