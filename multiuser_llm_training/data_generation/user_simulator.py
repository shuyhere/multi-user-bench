import random
from typing import Dict, List
from api_client import call_model

class UserSimulator:
    def __init__(self, model="deepseek/deepseek-chat-v3-0324", temperature=0.8):
        self.model = model
        self.temperature = temperature
    
    def generate_user_message(
        self,
        user_profile: Dict,
        scenario_context: Dict,
        conversation_history: List[Dict],
        turn_number: int
    ) -> str:
        """
        Generate a single user message using structured chat messages
        """
        messages = self._build_messages(user_profile, scenario_context, conversation_history, turn_number)
        
        content = call_model(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=16384
        )
        
        return content.strip()
    
    def _build_messages(
        self,
        user_profile: Dict,
        scenario_context: Dict,
        conversation_history: List[Dict],
        turn_number: int
    ) -> List[Dict]:
        """Build structured messages list for user simulator"""
        
        # Identify other participants for valid addressing
        other_participants = [p['id'] for p in scenario_context['participants'] if p['id'] != user_profile['id']]
        valid_targets = [f"@{p}" for p in other_participants] + ["@Agent"]
        
        system_prompt = f"""You are simulating a user in a multi-user conversation.
        
**Your Character:**
- Name: {user_profile['id']}
- Role: {user_profile['role']}
- Background: {user_profile['background']}

**Scenario Environment:** {scenario_context.get('scenario_description', '')}

**Valid Participants to Address:**
{', '.join(valid_targets)}

**Instructions:**
1. Stay in character!
2. **Addressing Rules:**
   - **Start of Message:** Optional. Use '@UserName:' or '@Agent:' to reply to someone specific. Omit to broadcast.
   - **In Message:** Use '@UserName' to mention others in the text.
   - Example: "@Lisa: I agree, but @Kevin needs to approve first."
3. Be natural and conversational.
4. Keep messages concise (under 3 sentences).
5. **Behavior:** {user_profile.get('behavior_cue', 'If your character background implies it, you can be off-topic, bored, or disruptive.')}
6. Only output the message content.
"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add limited conversation history for context
        for msg in conversation_history[-10:]:
            role = msg.get('role', 'Unknown')
            content = msg.get('message', '')
            
            if role == user_profile['id']:
                messages.append({"role": "assistant", "content": content})
            elif role == 'assistant':
                messages.append({"role": "user", "name": "Agent", "content": f"[Agent]: {content}"})
            else:
                messages.append({"role": "user", "name": role, "content": f"[{role}]: {content}"})
                
        # Final instruction as a user message
        messages.append({
            "role": "user", 
            "content": f"It is now your turn to speak. What do you say next as {user_profile['id']}?"
        })
        
        return messages
    
    def generate_multi_user_messages(
        self,
        participants: List[Dict],
        scenario_context: Dict,
        num_user_messages: int = 3
    ) -> List[Dict]:
        """
        Generate initial user messages from multiple users
        
        Returns:
            List of {"speaker": user_id, "message": content}
        """
        messages = []
        conversation_history = []
        
        # Randomly select users to speak
        speaking_users = random.sample(participants, min(num_user_messages, len(participants)))
        
        for user in speaking_users:
            message = self.generate_user_message(
                user_profile=user,
                scenario_context=scenario_context,
                conversation_history=conversation_history,
                turn_number=len(messages) + 1
            )
            
            msg_obj = {
                "speaker": user['id'],
                "message": message,
                "type": "public"
            }
            messages.append(msg_obj)
            conversation_history.append(msg_obj)
        
        return messages
