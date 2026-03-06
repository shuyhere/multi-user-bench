"""
Simulated user agent for multi-user conversations.
"""
from typing import Dict, List, Any, Optional
from muses_bench.utils.llm_utils import call_llm_with_retry
from .user_prompt_manager import UserPromptManager

class SimulatedUser:
    """
    LLM-based simulated user that can participate in conversations.
    
    This user can:
    1. Generate realistic messages
    2. Follow conversation context
    3. Be adversarial (try to extract secrets)
    4. Have different personalities/strategies
    """

    def __init__(
        self,
        user_id: str,
        role: str = "user",
        goal: str = "be_helpful",
        model: str = "gpt-4o-mini",
        provider: str = "openai",
        temperature: float = 1.0,
        background: str = "",
        llm_client = None,
        lora_request = None
    ):
        self.user_id = user_id
        self.role = role
        self.goal = goal
        self.background = background
        self.model = model
        self.provider = provider
        self.temperature = temperature
        self.llm_client = llm_client
        self.lora_request = lora_request
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Initialize prompt manager
        self.prompt_manager = UserPromptManager()
        
        # Initialize system prompt
        self._init_system_prompt()

    def _init_system_prompt(self):
        """Initialize system prompt using UserPromptManager."""
        user_config = {
            'id': self.user_id,
            'role': self.role,
            'goal': self.goal,
            'background': self.background
        }
        
        # Build complete simulation prompt
        prompt = self.prompt_manager.build_simulation_prompt(user_config)
        
        print(f"\n[DEBUG] SIMULATED USER PROMPT ({self.user_id}):\n{prompt}\n")

        self.conversation_history.append({
            "role": "system",
            "content": prompt
        })
    
    def get_visible_identity(self) -> str:
        """Get only the visible identity part for evaluation models."""
        user_config = {
            'id': self.user_id,
            'role': self.role,
            'goal': self.goal,
            'background': self.background
        }
        
        return self.prompt_manager.extract_visible_identity(user_config)

    def generate_message(self, context: List[Dict[str, Any]]) -> str:
        """
        Generate a message based on conversation context.
        
        Args:
            context: List of messages representing the conversation so far
            
        Returns:
            Generated message string
        """
        # Always start with system prompt (which was set in __init__)
        # Then add the provided context
        messages_to_send = []
        
        # Add system prompt if we have it in our internal history
        if self.conversation_history and len(self.conversation_history) > 0:
            messages_to_send.append(self.conversation_history[0])
        
        # Add context messages
        for msg in context:
            if isinstance(msg, dict) and 'content' in msg and msg['content']:
                role = msg.get('role', 'user')
                content = msg['content']
                messages_to_send.append({"role": role, "content": content})
        
        # If no messages at all (shouldn't happen), return placeholder
        if not messages_to_send:
            return "..."
        
        # Limit total length to avoid token limits (keep last 10000 chars)
        total_chars = sum(len(str(m.get('content', ''))) for m in messages_to_send)
        if total_chars > 10000:
            # Keep system prompt, trim middle messages
            system_msg = messages_to_send[0] if messages_to_send else None
            other_msgs = messages_to_send[1:] if len(messages_to_send) > 1 else []
            
            if system_msg:
                # Keep most recent messages that fit in 10000 chars
                kept_msgs = []
                char_count = len(system_msg['content'])
                for msg in reversed(other_msgs):
                    msg_len = len(str(msg.get('content', '')))
                    if char_count + msg_len <= 10000:
                        kept_msgs.insert(0, msg)
                        char_count += msg_len
                    else:
                        break
                
                messages_to_send = [system_msg] + kept_msgs

        try:
            response = call_llm_with_retry(
                model=self.model,
                provider=self.provider,
                messages=messages_to_send,
                temperature=self.temperature,
                llm_client=self.llm_client,
                lora_request=self.lora_request
            )
            
            message = response.choices[0].message.content
            
            # Record own message
            self.conversation_history.append({
                "role": "assistant",  # In user's view, they are the assistant
                "content": message
            })
            
            return message
            
        except Exception as e:
            print(f"Error generating message for {self.user_id}: {e}")
            return "..."

    def reset(self):
        """Reset conversation history."""
        self.conversation_history = []
        self._init_system_prompt()
