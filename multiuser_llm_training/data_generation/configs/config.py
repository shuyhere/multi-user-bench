"""
Configuration for multi-user conversation generation
"""

# Model configurations
# Model configurations
USER_SIMULATOR_MODEL = "deepseek/deepseek-chat"
TEACHER_MODEL = "openai/gpt-5.1"
CANDIDATE_MODELS = [
    "openai/gpt-5.1",
    "google/gemini-3-flash-preview",
    "anthropic/claude-haiku-4.5",
    "x-ai/grok-4.1-fast"
]

# Generation parameters
MIN_USERS = 2
MAX_USERS = 10
MIN_TURNS = 1  # Single-turn conversations
MAX_TURNS = 10  # Max agent turns

# Conversation distribution
TURN_DISTRIBUTION = {
    "single_turn": 0.2,    # 20% single-turn (1 turn)
    "short": 0.4,          # 40% short (2-5 turns)
    "medium": 0.4,         # 40% medium (6-10 turns)
    "long": 0.0,           # 0% long
}

# Scenario categories
SCENARIO_CATEGORIES = [
    "it_support",
    "project_collaboration",
    "customer_service",
    "healthcare_advisory",
    "education",
    "event_planning",
    "legal_consultation",
    "financial_planning",
    "travel_coordination",
    "crisis_management",
    "scientific_research"
]

# Generation settings
BATCH_SIZE = 10
NUM_SCENARIOS_PER_CATEGORY = 20
TEMPERATURE = 1.0
MAX_RETRIES = 3
MAX_WORKERS = 10

# Quality filtering thresholds
MIN_AGENT_RESPONSES = 1
MIN_USER_MESSAGES = 1
MAX_PRIVATE_MESSAGE_RATIO = 0.2  # Max 50% private messages
