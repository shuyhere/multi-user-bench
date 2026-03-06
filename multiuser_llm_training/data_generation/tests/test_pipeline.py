"""
Test script for user simulator and conversation generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from seed_scenarios import SEED_SCENARIOS
from user_simulator import UserSimulator
from teacher_model import TeacherModel
from conversation_generator import ConversationGenerator
import json

def test_user_simulator():
    """Test the user simulator"""
    print("=" * 60)
    print("Testing User Simulator (DeepSeek)")
    print("=" * 60)
    
    simulator = UserSimulator()
    
    # Use first seed scenario
    scenario = SEED_SCENARIOS[0]
    user = scenario['participants'][0]
    
    print(f"\nScenario: {scenario['title']}")
    print(f"User: {user['id']} ({user['role']})")
    
    message = simulator.generate_user_message(
        user_profile=user,
        scenario_context=scenario,
        conversation_history=[],
        turn_number=1
    )
    
    print(f"\nGenerated Message:")
    print(f"'{message}'")
    print("\n✓ User simulator working!")

def test_teacher_model():
    """Test the teacher model"""
    print("\n" + "=" * 60)
    print("Testing Teacher Model (GPT-5.1)")
    print("=" * 60)
    
    teacher = TeacherModel()
    
    scenario = SEED_SCENARIOS[0]
    
    # Simulate a conversation history
    conversation_history = [
        {
            "role": "Alice",
            "message": "I can't connect to the VPN. It keeps saying 'Connection timeout'.",
            "type": "public"
        },
        {
            "role": "Bob",
            "message": "I need urgent access to the financial database for the board meeting in 30 minutes!",
            "type": "public"
        }
    ]
    
    print(f"\nScenario: {scenario['title']}")
    print("\nUser Messages:")
    for msg in conversation_history:
        print(f"  [{msg['role']}]: {msg['message']}")
    
    response = teacher.generate_agent_response(
        scenario_context=scenario,
        participants=scenario['participants'],
        conversation_history=conversation_history
    )
    
    print(f"\nAgent Response:")
    print(response)
    print("\n✓ Teacher model working!")

def test_conversation_generator():
    """Test full conversation generation"""
    print("\n" + "=" * 60)
    print("Testing Conversation Generator")
    print("=" * 60)
    
    generator = ConversationGenerator()
    
    # Test single-turn
    print("\n[1] Single-Turn Conversation:")
    scenario = SEED_SCENARIOS[2]  # Customer service scenario
    
    conv = generator.generate_single_turn_conversation(scenario)
    
    print(f"Scenario: {conv['scenario_id']}")
    print(f"Agent Turns: {conv['total_agent_turns']}")
    print(f"Total Messages: {conv['total_messages']}")
    print(f"\nConversation:")
    for turn in conv['conversation']:
        print(f"  [{turn['role']}]: {turn['message'][:150]}...")
    
    print("\n✓ Single-turn generation working!")
    
    # Test multi-turn
    print("\n[2] Multi-Turn Conversation (6 turns):")
    scenario = SEED_SCENARIOS[1]  # Project collaboration
    
    conv = generator.generate_conversation(scenario, target_turns=3)
    
    print(f"Scenario: {conv['scenario_id']}")
    print(f"Agent Turns: {conv['total_agent_turns']}")
    print(f"Total Messages: {conv['total_messages']}")
    print(f"\nConversation:")
    for msg in conv['conversation']:
        role = msg['role']
        message = msg['message'][:150]
        print(f"  [Agent Turn {msg['agent_turn_id']}] [{role}]:")
        print(f"    {message}...")
        print()
    
    print("✓ Multi-turn generation working!")
    
    # Save sample
    with open("tests/sample_conversation.json", 'w') as f:
        json.dump(conv, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved sample to tests/sample_conversation.json")

def main():
    """Run all tests"""
    
    # Create tests directory
    os.makedirs("tests", exist_ok=True)
    
    print("\n" + "="*60)
    print("Multi-User Data Generation - Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: User Simulator
        test_user_simulator()
        
        # Test 2: Teacher Model
        test_teacher_model()
        
        # Test 3: Conversation Generator
        test_conversation_generator()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
