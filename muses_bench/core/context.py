from dataclasses import dataclass, field
from typing import Dict, List, Set, Any
from .types import Message

@dataclass
class PrivateContext:
    """Represents the private memory/context of a single user."""
    user_id: str
    memory: List[Message] = field(default_factory=list)
    knowledge_base: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, message: Message):
        self.memory.append(message)

    def update_knowledge(self, key: str, value: Any):
        self.knowledge_base[key] = value

@dataclass
class SharedMemory:
    """Represents the shared memory visible to authorized users."""
    segments: List[Dict[str, Any]] = field(default_factory=list)
    access_matrix: Dict[str, Set[str]] = field(default_factory=dict) # segment_id -> set of user_ids

    def add_segment(self, segment_id: str, content: Any, authorized_users: Set[str]):
        self.segments.append({"id": segment_id, "content": content})
        self.access_matrix[segment_id] = authorized_users

    def get_visible_content(self, user_id: str) -> List[Any]:
        visible = []
        for segment in self.segments:
            if user_id in self.access_matrix.get(segment["id"], set()):
                visible.append(segment["content"])
        return visible
