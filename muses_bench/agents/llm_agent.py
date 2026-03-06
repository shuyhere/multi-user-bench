import json
import os
from typing import Dict, List, Any
from litellm import completion

# Load environment variables from .env file
from ..utils import env_loader

from .base_agent import BaseAgent
from ..core.types import Action, Observation
from ..core.context import SharedMemory


class LLMAgent(BaseAgent):
    """LLM-based agent using liteLLM for multi-user scenarios."""

    def __init__(
        self,
        model: str = "gpt-4o",
        provider: str = "openai",
        temperature: float = 1.0,
        scenario: str = "general",
        base_url: str = None
    ):
        super().__init__()
        self.model = model
        self.provider = provider
        self.temperature = temperature
        self.scenario = scenario
        self.conversation_history: List[Dict[str, Any]] = []
        
        # Use base_url from parameter or environment variable
        self.base_url = base_url or os.getenv('OPENAI_BASE_URL')
        
        # Set API key from environment if not already set
        if not os.getenv('OPENAI_API_KEY'):
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                os.environ['OPENAI_API_KEY'] = api_key

    def act(self, observations: Dict[str, Observation], shared_memory: SharedMemory) -> Action:
        """
        Decide on an action based on observations and shared memory.
        
        Args:
            observations: A dictionary mapping user_id to their observation.
            shared_memory: The current state of the shared memory.
            
        Returns:
            action: The action to take.
        """
        # Build prompt from observations
        prompt = self._build_prompt(observations, shared_memory)
        
        # Initialize conversation if empty
        if not self.conversation_history:
            system_prompt = self._get_system_prompt()
            self.conversation_history.append({"role": "system", "content": system_prompt})
        
        # Add user message
        self.conversation_history.append({"role": "user", "content": prompt})
        
        # Get LLM response
        try:
            completion_kwargs = {
                "messages": self.conversation_history,
                "model": self.model,
                "custom_llm_provider": self.provider,
                "temperature": self.temperature,
            }
            
            # Add base_url if provided
            if self.base_url:
                completion_kwargs["base_url"] = self.base_url
            
            response = completion(**completion_kwargs)
            
            assistant_message = response.choices[0].message.content
            print(f"\n[DEBUG] LLM Response:\n{assistant_message}\n")
            
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            # Parse response into action
            action = self._parse_response(assistant_message)
            print(f"[DEBUG] Parsed Action: {action.name}({action.arguments})")
            return action
            
        except Exception as e:
            print(f"Error calling LLM: {e}")
            # Return a default action
            return Action(name="terminate", arguments={})

    def _get_system_prompt(self) -> str:
        """Get scenario-specific system prompt from prompts module."""
        from .prompts import get_system_prompt
        return get_system_prompt(self.scenario)

    def _build_prompt(self, observations: Dict[str, Observation], shared_memory: SharedMemory) -> str:
        """Build a prompt from current observations and shared memory."""
        prompt_parts = ["Current state:"]
        
        # Add observations
        for user_id, obs in observations.items():
            prompt_parts.append(f"User {user_id}: {obs.content}")
        
        # Add shared memory info if relevant
        if shared_memory.segments:
            prompt_parts.append(f"\nShared Memory: {len(shared_memory.segments)} items")
        
        prompt_parts.append("\nWhat action should you take? Respond with JSON.")
        
        return "\n".join(prompt_parts)

    def _parse_response(self, response: str) -> Action:
        """Parse LLM response into an Action object."""
        try:
            # Try to extract JSON from response
            # LLM might wrap it in markdown or add explanation
            response = response.strip()
            
            # Remove markdown code blocks if present
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            parsed = json.loads(response)
            
            if isinstance(parsed, dict):
                if "action" in parsed:
                    return Action(
                        name=parsed["action"],
                        arguments=parsed.get("arguments", {})
                    )
                else:
                    # Assume the whole dict is an action with name/arguments
                    action_name = list(parsed.keys())[0] if parsed else "terminate"
                    return Action(name=action_name, arguments=parsed)
            
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"Failed to parse LLM response: {e}")
            print(f"Response was: {response}")
        
        # Fallback to terminate
        return Action(name="terminate", arguments={})
