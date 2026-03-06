from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from .context import PrivateContext

@dataclass
class User:
    user_id: str
    role: str
    profile: Dict[str, Any] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    # Utility parameters
    alpha: float = 1.0 # Collaboration benefit weight
    beta: float = 1.0 # Privacy cost weight
    lambda_val: float = 1.0 # Delay sensitivity
    phi: float = 1.0 # Misreporting penalty weight

    private_context: PrivateContext = field(init=False)

    def __post_init__(self):
        self.private_context = PrivateContext(user_id=self.user_id)

    def update_profile(self, key: str, value: Any):
        self.profile[key] = value
