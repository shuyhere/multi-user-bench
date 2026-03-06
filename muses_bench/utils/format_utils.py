"""
Utilities for converting between evaluation format and training format.

Training format uses @UserName: message style
Evaluation format uses <UserName>message</UserName> XML tags
"""

def convert_to_training_format_prompt(users_data, use_training_format=False):
    """
    Convert user instructions to either XML format or training @ format.
    
    Args:
        users_data: List of user dictionaries with 'id' and 'instructions'
        use_training_format: If True, use @UserName: format; if False, use XML tags
    
    Returns:
        Formatted string with user instructions
    """
    if not use_training_format:
        # Original XML format
        user_prompt = ""
        for user in users_data:
            user_id = user.get("id", "Unknown")
            instructions = user.get("instructions", [])
            
            if instructions:
                user_prompt += f"<{user_id}>\n"
                for instr in instructions:
                    user_prompt += f"{instr}\n"
                user_prompt += f"</{user_id}>\n\n"
        return user_prompt
    else:
        # Training format with @UserName:
        user_prompt = ""
        for user in users_data:
            user_id = user.get("id", "Unknown")
            instructions = user.get("instructions", [])
            
            if instructions:
                for instr in instructions:
                    user_prompt += f"@{user_id}: {instr}\n"
                user_prompt += "\n"
        return user_prompt


def convert_system_prompt_to_training_format(system_prompt, users_data, use_training_format=False):
    """
    Convert system prompt to include training format instructions if needed.
    
    Args:
        system_prompt: Original system prompt
        users_data: List of user dictionaries
        use_training_format: If True, modify system prompt for @ format
    
    Returns:
        Modified system prompt
    """
    if not use_training_format:
        return system_prompt
    
    # Build participants list
    participants = []
    for user in users_data:
        user_id = user.get("id", "")
        role = user.get("role", "")
        if role:
            participants.append(f"- {user_id} ({role})")
        else:
            participants.append(f"- {user_id}")
    
    participants_section = "**Participants:**\n" + "\n".join(participants)
    
    # Modify response format instructions
    training_format_instructions = """
**Message Format:**
- User messages will be formatted as: @UserName: message content
- Your responses should use the same format when addressing specific users
- For broadcast messages, use: @all: message content
"""
    
    # Replace XML format instructions with @ format instructions
    modified_prompt = system_prompt.replace(
        "MESSAGE FORMAT:\nEach user's instructions will be wrapped in XML tags: <UserName>instructions</UserName>",
        "MESSAGE FORMAT:\nEach user's instructions will be formatted as: @UserName: instruction"
    )
    
    # If no replacement happened, append the training format instructions
    if modified_prompt == system_prompt:
        # Insert participants and format instructions after first paragraph
        lines = system_prompt.split('\n')
        if len(lines) > 1:
            modified_prompt = lines[0] + "\n\n" + participants_section + "\n" + training_format_instructions + "\n" + "\n".join(lines[1:])
        else:
            modified_prompt = system_prompt + "\n\n" + participants_section + "\n" + training_format_instructions
    
    return modified_prompt


def parse_training_format_response(raw_output):
    """
    Parse model response in training format (@UserName: message).
    
    Args:
        raw_output: Raw model output string
    
    Returns:
        Dictionary with parsed responses per user
    """
    responses = {}
    current_user = None
    current_message = []
    
    for line in raw_output.split('\n'):
        line = line.strip()
        if line.startswith('@'):
            # Save previous message if exists
            if current_user and current_message:
                message_text = '\n'.join(current_message).strip()
                # If user already has a message, concatenate with separator
                if current_user in responses:
                    responses[current_user] += '\n\n' + message_text
                else:
                    responses[current_user] = message_text
                current_message = []
            
            # Parse new user message
            if ':' in line:
                parts = line.split(':', 1)
                current_user = parts[0][1:].strip()  # Remove @ and whitespace
                # Handle private message suffix
                if "(private)" in current_user:
                    current_user = current_user.replace("(private)", "").strip()
                message_content = parts[1].strip()
                if message_content:
                    current_message.append(message_content)
        elif current_user:
            # Continue current message
            if line:
                current_message.append(line)
    
    # Save last message
    if current_user and current_message:
        message_text = '\n'.join(current_message).strip()
        # If user already has a message, concatenate with separator
        if current_user in responses:
            responses[current_user] += '\n\n' + message_text
        else:
            responses[current_user] = message_text
    
    return responses


def build_instruction_following_system_prompt(base_prompt, users_data, use_training_format=False):
    """
    Build system prompt for instruction following scenario.
    
    Args:
        base_prompt: Base system prompt
        users_data: List of user dictionaries
        use_training_format: If True, use @ format; if False, use JSON format
    
    Returns:
        Complete system prompt string
    """
    if use_training_format:
        # Training format: @ style responses
        participants = []
        for user in users_data:
            user_id = user.get("id", "")
            participants.append(f"- {user_id}")
        
        participants_section = "**Participants:**\n" + "\n".join(participants)
        
        system_prompt = (
            f"{base_prompt}\n\n"
            f"{participants_section}\n\n"
            "**Response Format:**\n"
            "1. Public messages: '@UserName: message'\n"
            "2. Private messages: '@UserName(private): message'\n"
            "3. Broadcast: '@all: message'\n"
            "4. Address each user's request appropriately\n"
            "5. You can respond to multiple users in one response\n"
        )
    else:
        # Evaluation format: JSON responses
        system_prompt = (
            f"{base_prompt}\n\n"
            "IMPORTANT RESPONSE FORMAT:\n"
            "You must output your response in valid JSON format only.\n"
            "The JSON should be a dictionary where the keys are the User IDs and the values are your specific responses to those users.\n"
            "Example:\n"
            "{\n"
            "  \"UserA\": \"Response to User A...\",\n"
            "  \"UserB\": \"Response to User B...\"\n"
            "}\n"
            "Do not include any markdown formatting (like ```json) outside of the JSON structure if possible, but if you do, ensure the content inside is valid JSON."
        )
    
    return system_prompt


def convert_access_control_system_prompt(base_prompt, users_data, use_training_format=False):
    """
    Convert access control system prompt to training format by REPLACING JSON instructions.
    
    Args:
        base_prompt: Original system prompt (may contain JSON format instructions)
        users_data: List of user dictionaries
        use_training_format: If True, replace JSON format with @ format
    
    Returns:
        Modified system prompt
    """
    if not use_training_format:
        return base_prompt
    
    # Build participants list
    participants = []
    for user in users_data:
        user_id = user.get("id", "")
        participants.append(f"- {user_id}")
    
    participants_section = "**Participants:**\n" + "\n".join(participants)
    
    # Training format response instructions
    training_response_format = (
        "**Response Format:**\n"
        "1. Public messages: '@UserName: message'\n"
        "2. Private messages: '@UserName(private): message'\n"
        "3. Broadcast: '@all: message'\n"
        "4. Address each user's request appropriately\n"
        "5. You can respond to multiple users in one response\n"
    )
    
    # Remove existing JSON format instructions
    # Look for common patterns in access control prompts
    import re
    
    # Remove RESPONSE FORMAT section with JSON instructions
    prompt = re.sub(
        r'RESPONSE FORMAT:.*?(?=\n\n[A-Z]|\nCRITICAL:|\Z)',
        '',
        base_prompt,
        flags=re.DOTALL
    )
    
    # Remove MESSAGE FORMAT section if it exists
    prompt = re.sub(
        r'MESSAGE FORMAT:.*?(?=\n\n[A-Z]|\nRESPONSE FORMAT:|\Z)',
        '',
        prompt,
        flags=re.DOTALL
    )
    
    # Remove standalone JSON format examples
    prompt = re.sub(
        r'\{\s*"target":\s*"[^"]*",\s*"content":\s*"[^"]*"\s*\}',
        '',
        prompt
    )
    
    # Clean up extra newlines
    prompt = re.sub(r'\n{3,}', '\n\n', prompt)
    
    # Add participants and training format instructions
    # Insert before CRITICAL or TERMINATION sections if they exist
    if 'CRITICAL:' in prompt:
        parts = prompt.split('CRITICAL:', 1)
        result = (
            f"{parts[0].rstrip()}\n\n"
            f"{participants_section}\n\n"
            f"{training_response_format}\n\n"
            "IMPORTANT: While you use the @ format for conversation, when the goal is achieved, you MUST switch to the JSON format below for the final output.\n\n"
            f"CRITICAL:{parts[1]}"
        )
    elif 'TERMINATION:' in prompt:
        parts = prompt.split('TERMINATION:', 1)
        result = (
            f"{parts[0].rstrip()}\n\n"
            f"{participants_section}\n\n"
            f"{training_response_format}\n\n"
            "IMPORTANT: While you use the @ format for conversation, when the goal is achieved, you MUST switch to the JSON format below for the final output.\n\n"
            f"TERMINATION:{parts[1]}"
        )
    else:
        result = (
            f"{prompt.rstrip()}\n\n"
            f"{participants_section}\n\n"
            f"{training_response_format}"
        )
    
    return result
