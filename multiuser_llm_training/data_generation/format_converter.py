"""
Format Converter
Converts generated conversations to training format
"""

import json
from typing import Dict, List

class FormatConverter:
    def __init__(self):
        pass
    
    def convert_to_training_format(self, conversation_data: Dict) -> Dict:
        """
        Convert conversation to Hugging Face chat template format
        
        Input: Raw conversation from generator
        Output: {"messages": [...]} format for training
        """
        scenario = conversation_data
        participants = scenario['participants']
        conversation = scenario['conversation']
        
        # Build system prompt
        system_prompt = self._build_system_prompt(scenario, participants)
        
        # Initialize messages with system prompt
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation turns
        for turn in conversation:
            role = turn['role']
            message = turn['message']
            
            if role == 'assistant':
                messages.append({
                    "role": "assistant",
                    "content": message
                })
            else:
                # User messages with user-specific role
                messages.append({
                    "role": f"user_{role}",
                    "content": message
                })
        
        return {"messages": messages}
    
    def _build_system_prompt(self, scenario: Dict, participants: List[Dict]) -> str:
        """Build system prompt for training"""
        
        category = scenario.get('category', 'general')
        
        agent_roles = {
            "it_support": "IT Support Assistant",
            "project_collaboration": "Project Management Assistant",
            "customer_service": "Customer Service Agent",
            "healthcare_advisory": "Health Advisory Assistant",
            "education": "Teaching Assistant"
        }
        
        agent_role = agent_roles.get(category, "Helpful Assistant")
        
        prompt = f"""You are a {agent_role} managing a multi-user conversation.

**Participants:**
"""
        for user in participants:
            prompt += f"- {user['id']} ({user['role']}): {user['background']}\n"
        
        prompt += """
**Response Format:**
1. Public messages: '@UserName: message'
2. Private messages: '@UserName(private): message'
3. Broadcast: '@all: message'
4. Use private messages for sensitive information
5. Help coordinate and resolve conflicts professionally
"""
        
        return prompt
    
    def batch_convert(self, conversations: List[Dict], output_path: str):
        """
        Convert multiple conversations and save to JSONL
        
        Args:
            conversations: List of conversation dictionaries
            output_path: Path to save JSONL file
        """
        with open(output_path, 'w') as f:
            for conv in conversations:
                training_data = self.convert_to_training_format(conv)
                f.write(json.dumps(training_data, ensure_ascii=False) + '\n')
        
        print(f"Converted {len(conversations)} conversations to {output_path}")
