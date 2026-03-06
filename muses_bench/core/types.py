from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

@dataclass
class Action:
    name: str
    arguments: Dict[str, Any]

@dataclass
class Observation:
    content: str
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class Message:
    role: str  # "user", "agent", "system"
    content: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None
