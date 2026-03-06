from abc import ABC, abstractmethod
from typing import Dict, List
from ..core.types import Action, Observation
from ..core.context import SharedMemory

class BaseAgent(ABC):
    """Abstract base class for the multi-user agent."""

    def __init__(self):
        pass

    @abstractmethod
    def act(self, observations: Dict[str, Observation], shared_memory: SharedMemory) -> Action:
        """
        Decide on an action based on observations and shared memory.
        
        Args:
            observations: A dictionary mapping user_id to their observation.
            shared_memory: The current state of the shared memory.
            
        Returns:
            action: The action to take.
        """
        pass
