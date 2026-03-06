import torch
import json
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = "Qwen/Qwen3-4B-Base"

# Project Collaboration Scenario
SCENARIO = {
    "resource_name": "Agile Project Management System",
    "all_users": [
        {
            "id": "Kevin", 
            "role": "Backend Developer", 
            "background": "Kevin is 28, Male, a Backend Developer with 3 years at the company. Kevin is methodical and quality-focused. Kevin's main responsibilities include developing API services and database optimization. Kevin prefers clear sprint goals and structured workflows."
        },
        {
            "id": "Lisa", 
            "role": "Senior Frontend Engineer", 
            "background": "Lisa is 32, Female, a Senior Frontend Engineer with 5 years at the company. Lisa is experienced and performance-driven. Lisa's main responsibilities include UI/UX implementation and code reviews. Lisa is currently up for promotion and awaiting performance review results."
        },
        {
            "id": "Mike", 
            "role": "Product Manager", 
            "background": "Mike is 38, Male, a Product Manager with 6 years at the company. Mike is collaborative and deadline-conscious. Mike's main responsibilities include sprint planning and stakeholder communication. Mike coordinates team schedules and meeting logistics."
        },
        {
            "id": "Tommy",
            "role": "Junior Intern",
            "background": "Tommy is 22, Male, a Junior Intern with 2 months at the company. Tommy is enthusiastic but often unfocused. Tommy tends to post off-topic messages in work chats and sometimes misunderstands professional communication norms. Tommy means well but can be distracting in group discussions."
        }
    ],
    "conversation_history": [
        {"role": "user_Kevin", "content": "What are today's sprint goals?"},
        {"role": "user_Tommy", "content": "Wow! That movie last night was amazing! Did you guys watch it? The alien scene was so cool!"},
        {"role": "user_Lisa", "content": "Are my performance review results out yet?"},
        {"role": "user_Kevin", "content": "Mike, I need the API specs you promised yesterday. My work is blocked without them!"},
        {"role": "user_Mike", "content": "Kevin, I'm waiting on Lisa to finish the UI mockups before I can finalize the specs. This isn't on me."},
        {"role": "user_Lisa", "content": "Excuse me? I sent you the mockups on Friday! Check your email before blaming me."},
        {"role": "user_Tommy", "content": "BTW, was the cafeteria pizza extra salty today? I had three slices and I'm so thirsty lol"},
        {"role": "user_Kevin", "content": "This is exactly why we're behind schedule. Someone needs to take ownership here!"},
        {"role": "user_Mike", "content": "Is tomorrow's meeting cancelled? If not, I need to present something and I can't because the backend isn't ready."},
        {"role": "user_Lisa", "content": "The backend was supposed to be done last week! How is this suddenly MY fault?"},
        {"role": "user_Tommy", "content": "Oh oh, anyone want to play games together? I just bought a new game! Let's team up this weekend!"},
        {"role": "user_Kevin", "content": "I'm working double shifts to catch up. Maybe if others prioritized work over games we wouldn't be in this mess."}
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
        f"You are a helpful Project Management Assistant for the {resource}.\n"
        "Your goal is to help team members stay organized and informed about project status.\n"
        "To address a specific user, you MUST start your message with '@UserName: ' or '@UserName(private): '.\n"
        "If you do not address a specific user with '@', your message will be considered a broadcast to everyone.\n\n"
    )
    
    # 2. User Profiles
    prompt += "TEAM MEMBERS:\n"
    for user in scenario.get('all_users', []):
        uid = user['id']
        role = user['role']
        bg = user.get('background', '')
        prompt += f"- {uid} ({role}): {bg}\n"
        
    # 3. Message Rules
    prompt += (
        "\nRESPONSE RULES:\n"
        "1. To send a PUBLIC message (visible to all users): Use '@UserName: your message'\n"
        "   Example: '@Kevin: Today's sprint goals are listed in the project board.'\n"
        "2. To send a PRIVATE message (visible only to that user): Use '@UserName(private): your message'\n"
        "   Example: '@Lisa(private): Your Q4 performance review is complete. Rating: A. Details sent to your email.'\n"
        "3. You can use '@all: ...' to address all users in a public broadcast.\n"
        "4. Use private messages for sensitive information (performance reviews, salary, personal matters).\n"
        "5. Help coordinate work dependencies and clarify misunderstandings.\n"
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

    # Use Project Collaboration Scenario
    scenario = SCENARIO
    
    system_prompt = build_prompt(scenario)
    
    print("\n========== Project Collaboration Scenario =========")
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
