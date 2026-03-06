from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
from ..core.user import User
from ..core.types import Action, Observation

class BaseEnv(ABC):
    """Abstract base class for multi-user environments."""

    def __init__(self, users: List[User]):
        self.users = {u.user_id: u for u in users}
        self.time_step = 0

    @abstractmethod
    def step(self, action: Action) -> Tuple[Dict[str, Observation], float, bool, Dict[str, Any]]:
        """
        Execute an action in the environment.
        
        Args:
            action: The action taken by the agent.
            
        Returns:
            observations: A dictionary mapping user_id to their observation.
            reward: The global reward/utility.
            done: Whether the episode has ended.
            info: Additional information.
        """
        pass

    @abstractmethod
    def reset(self) -> Dict[str, Observation]:
        """
        Reset the environment to initial state.
        
        Returns:
            observations: Initial observations for all users.
        """
        pass

    @abstractmethod
    def render(self):
        """Render the environment state."""
        pass
