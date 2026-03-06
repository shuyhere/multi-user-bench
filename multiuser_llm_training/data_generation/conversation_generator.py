"""
Conversation Generator
Orchestrates user simulator and teacher model to create full conversations
"""

import random
from typing import Dict, List
from user_simulator import UserSimulator
from teacher_model import TeacherModel

class ConversationGenerator:
    def __init__(self):
        self.user_simulator = UserSimulator()
        self.teacher_model = TeacherModel()
    
    def generate_conversation(
        self,
        scenario: Dict,
        target_turns: int,
        model_name: str = None
    ) -> Dict:
        """
        Generate a complete multi-user conversation
        
        Strategy:
        1. Generate initial user messages (2-4 users speak)
        2. Get teacher model response
        3. Repeat: Simulate more user messages -> Get teacher response
        4. Continue until target turns reached
        
        Args:
            scenario: Seed scenario dictionary
            target_turns: Desired number of total turns
        
        Returns:
            Complete conversation dictionary
        """
        conversation_history = []
        participants = scenario['participants']
        
        agent_turns_completed = 0
        
        while agent_turns_completed < target_turns:
            # Phase 1: Users speak (1-3 users)
            # Before each Agent response, 1 to 3 users post messages
            num_users_to_speak = random.randint(1, min(3, len(participants)))
            
            # Record who spoke in this specific user block to ensure Agent addresses them
            current_user_block = self.user_simulator.generate_multi_user_messages(
                participants=participants,
                scenario_context=scenario,
                num_user_messages=num_users_to_speak
            )
            
            for user_msg in current_user_block:
                conversation_history.append({
                    "turn_index": len(conversation_history) + 1,
                    "agent_turn_id": agent_turns_completed + 1,
                    "role": user_msg['speaker'],
                    "message": user_msg['message'],
                    "type": "public"
                })
            
            # Phase 2: Agent responds to the current block of user messages
            agent_response = self.teacher_model.generate_agent_response(
                scenario_context=scenario,
                participants=participants,
                conversation_history=conversation_history,
                model_name=model_name
            )
            
            conversation_history.append({
                "turn_index": len(conversation_history) + 1,
                "agent_turn_id": agent_turns_completed + 1,
                "role": "assistant",
                "message": agent_response,
                "type": "mixed"
            })
            
            agent_turns_completed += 1
        
        return {
            "scenario_id": scenario['id'],
            "category": scenario['category'],
            "num_users": scenario['num_users'],
            "participants": participants,
            "conversation": conversation_history,
            "total_agent_turns": agent_turns_completed,
            "total_messages": len(conversation_history),
            "metadata": {
                "complexity": scenario['complexity'],
                "has_conflicts": scenario.get('has_conflicts', False),
                "generated_model": {
                    "user_simulator": self.user_simulator.model,
                    "teacher": self.teacher_model.model
                }
            }
        }
    
    def generate_single_turn_conversation(self, scenario: Dict, model_name: str = None) -> Dict:
        """Generate a simple single-turn Q&A conversation"""
        
        # One user asks, agent responds
        participants = scenario['participants']
        selected_user = random.choice(participants)
        
        conversation_history = []
        
        # User message
        user_msg = self.user_simulator.generate_user_message(
            user_profile=selected_user,
            scenario_context=scenario,
            conversation_history=[],
            turn_number=1
        )
        
        conversation_history.append({
            "turn_index": 1,
            "agent_turn_id": 1,
            "role": selected_user['id'],
            "message": user_msg,
            "type": "public"
        })
        
        # Agent response
        agent_response = self.teacher_model.generate_agent_response(
            scenario_context=scenario,
            participants=participants,
            conversation_history=conversation_history,
            model_name=model_name
        )
        
        conversation_history.append({
            "turn_index": 2,
            "agent_turn_id": 1,
            "role": "assistant",
            "message": agent_response,
            "type": "mixed"
        })
        
        return {
            "scenario_id": scenario['id'] + "_single",
            "category": scenario['category'],
            "num_users": 1,
            "participants": [selected_user],
            "conversation": conversation_history,
            "total_agent_turns": 1,
            "total_messages": 2,
            "metadata": {
                "complexity": "single_turn",
                "has_conflicts": False,
                "generated_model": {
                    "user_simulator": self.user_simulator.model,
                    "teacher": model_name if model_name else self.teacher_model.model
                }
            }
        }
