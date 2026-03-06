from typing import Dict, List
from api_client import call_model

class TeacherModel:
    def __init__(self, model="openai/gpt-5.1", temperature=1.0):
        self.model = model
        self.temperature = temperature
    
    def generate_agent_response(
        self,
        scenario_context: Dict,
        participants: List[Dict],
        conversation_history: List[Dict],
        model_name: str = None
    ) -> str:
        """
        Generate agent response using structured chat messages
        """
        messages = self._build_messages(scenario_context, participants, conversation_history)
        
        content = call_model(
            model=model_name if model_name else self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=16384
        )
        
        return content.strip()
    
    def _build_messages(self, scenario_context: Dict, participants: List[Dict], conversation_history: List[Dict]) -> List[Dict]:
        """Build structured messages list for the teacher model"""
        
        # 1. System Prompt
        category = scenario_context.get('category', 'general')
        agent_roles = {
            "it_support": "IT Support Assistant",
            "project_collaboration": "Project Management Assistant",
            "customer_service": "Customer Service Agent",
            "healthcare_advisory": "Health Advisory Assistant",
            "education": "Teaching Assistant"
        }
        agent_role = agent_roles.get(category, "Helpful Assistant")
        
        system_content = f"You are a {agent_role} managing a multi-user conversation.\n\n"
        system_content += f"**Scenario:** {scenario_context.get('scenario_description', '')}\n\n"
        system_content += "**Participants:**\n"
        for user in participants:
            system_content += f"- {user['id']} ({user['role']}): {user['background']}\n"
        
        system_content += """
**Response Rules:**
1. **Primary Addressing (Reply):** Start your message with ONE primary target:
   - '@UserName: message' (Reply to specific user)
   - '@all: message' (Broadcast to everyone)
   - Do NOT chain multiple startup targets (e.g. no "@User1: @User2: ...").

2. **Secondary Mentions:** Inside the message body, you can mention others using '@UserName' normally.
   - Example: "@Mike: I agree, and @Kevin needs to see this too."

3. **Context:** Pay attention to both direct Mentions (@Agent) and broadcasts.
4. **Moderation:** If a user is being disruptive (off-topic, rude, spamming):
   - **MUST** send a **PRIVATE** warning: "@DisruptiveUser(private): [Firm warning to stay focused]".
   - **ALSO** send a **PUBLIC** redirect: "@all: [Let's keep the channel focused on work]".
   - Do this in the SAME turn (multi-paragraph response).
5. Provide helpful, professional, and clear answers.
6. Use separate paragraphs for different users.
7. Use private messages for sensitive information like passwords or personal evaluations.
"""
        
        messages = [{"role": "system", "content": system_content}]
        
        # 2. Conversation History
        for msg in conversation_history:
            role = msg.get('role', 'Unknown')
            content = msg.get('message', '')
            
            if role == 'assistant':
                # Skip empty agent messages from previous failed turns
                if not content: continue
                messages.append({"role": "assistant", "content": content})
            else:
                # Format user message to include their name
                # Role contains User ID in this case (e.g. "Mike")
                messages.append({
                    "role": "user", 
                    "name": role,
                    "content": f"[{role}]: {content}"
                })
        
        return messages
