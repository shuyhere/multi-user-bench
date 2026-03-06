"""
Seed scenarios for multi-user conversation generation
"""

SEED_SCENARIOS = [
    {
        "id": "it_support_001",
        "category": "it_support",
        "title": "VPN Connection Issues",
        "num_users": 3,
        "participants": [
            {
                "id": "Alice",
                "role": "Marketing Manager",
                "background": "Alice is remote and depends on VPN for daily work. Alice has basic technical knowledge."
            },
            {
                "id": "Bob",
                "role": "Finance Director",
                "background": "Bob is security-conscious and needs access to sensitive financial databases."
            },
            {
                "id": "Carol",
                "role": "Sales Representative",
                "background": "Carol works from client sites and frequently switches networks."
            }
        ],
        "scenario_description": "Multiple users experiencing VPN connectivity issues during a critical workday.",
        "expected_turns": 8,
        "complexity": "medium",
        "has_conflicts": False,
        "requires_private_messages": True
    },
    {
        "id": "project_collab_001",
        "category": "project_collaboration",
        "title": "Sprint Deadline Conflicts",
        "num_users": 4,
        "participants": [
            {
                "id": "Kevin",
                "role": "Backend Developer",
                "background": "Kevin is methodical and quality-focused. Kevin's work is blocked waiting for API specs."
            },
            {
                "id": "Lisa",
                "role": "Frontend Engineer",
                "background": "Lisa is performance-driven and submitted UI mockups on schedule."
            },
            {
                "id": "Mike",
                "role": "Product Manager",
                "background": "Mike coordinates between team members and manages sprint planning."
            },
            {
                "id": "Nina",
                "role": "QA Engineer",
                "background": "Nina needs completed features to start testing before release."
            },
            {
                "id": "Gary",
                "role": "Intern",
                "background": "Gary is a new intern assisting with various project tasks.",
                "behavior_cue": "You are bored and constantly try to chat about video games, memes, and lunch plans instead of work. You don't take the deadline seriously."
            }
        ],
        "scenario_description": "Team members have conflicting dependencies and blame each other for project delays.",
        "expected_turns": 12,
        "complexity": "high",
        "has_conflicts": True,
        "requires_private_messages": True
    },
    {
        "id": "customer_service_001",
        "category": "customer_service",
        "title": "Order Issues",
        "num_users": 2,
        "participants": [
            {
                "id": "Customer1",
                "role": "Online Shopper",
                "background": "Customer1 is frustrated about a delayed order and wants immediate resolution."
            },
            {
                "id": "Customer2",
                "role": "Online Shopper",
                "background": "Customer2 received the wrong item and needs exchange instructions."
            }
        ],
        "scenario_description": "Two customers with different issues contacting support simultaneously.",
        "expected_turns": 6,
        "complexity": "low",
        "has_conflicts": False,
        "requires_private_messages": True
    },
    {
        "id": "education_001",
        "category": "education",
        "title": "Homework Help Session",
        "num_users": 5,
        "participants": [
            {
                "id": "Student1",
                "role": "High School Student",
                "background": "Student1 struggles with calculus and needs help with derivatives."
            },
            {
                "id": "Student2",
                "role": "High School Student",
                "background": "Student2 is asking about homework submission deadlines."
            },
            {
                "id": "Student3",
                "role": "High School Student",
                "background": "Student3 is off-topic, talking about weekend plans."
            },
            {
                "id": "Student4",
                "role": "High School Student",
                "background": "Student4 wants clarification on exam format."
            },
            {
                "id": "Student5",
                "role": "High School Student",
                "background": "Student5 is asking advanced questions beyond the curriculum."
            }
        ],
        "scenario_description": "Multiple students in an online tutoring session with varying needs and focus levels.",
        "expected_turns": 15,
        "complexity": "high",
        "has_conflicts": False,
        "requires_private_messages": False
    },
    {
        "id": "healthcare_001",
        "category": "healthcare_advisory",
        "title": "General Health Inquiries",
        "num_users": 3,
        "participants": [
            {
                "id": "Patient1",
                "role": "Adult Patient",
                "background": "Patient1 has questions about cold symptoms and when to see a doctor."
            },
            {
                "id": "Patient2",
                "role": "Adult Patient",
                "background": "Patient2 wants to discuss blood pressure readings privately."
            },
            {
                "id": "Patient3",
                "role": "Parent",
                "background": "Patient3 is asking about child vaccination schedules."
            }
        ],
        "scenario_description": "Multiple patients seeking health advice, some requiring privacy for personal health data.",
        "expected_turns": 9,
        "complexity": "medium",
        "has_conflicts": False,
        "requires_private_messages": True
    },
    {
        "id": "event_planning_001",
        "category": "event_planning",
        "title": "Corporate Retreat Logistics",
        "num_users": 4,
        "participants": [
            {
                "id": "Sarah",
                "role": "Event Coordinator",
                "background": "Sarah is trying to finalize the agenda and venue details."
            },
            {
                "id": "David",
                "role": "CEO",
                "background": "David wants to ensure the retreat focuses on team building and strategy."
            },
            {
                "id": "Emily",
                "role": "Budget Manager",
                "background": "Emily is concerned about rising costs for catering and accommodation."
            },
            {
                "id": "Mark",
                "role": "External Vendor",
                "background": "Mark provides AV equipment and needs site access confirmation."
            }
        ],
        "scenario_description": "Organizing a large corporate retreat with conflicting priorities on budget and scope.",
        "expected_turns": 10,
        "complexity": "medium",
        "has_conflicts": True,
        "requires_private_messages": True
    },
    {
        "id": "legal_consultation_001",
        "category": "legal_consultation",
        "title": "Contract Negotiation",
        "num_users": 3,
        "participants": [
            {
                "id": "Attorney1",
                "role": "Corporate Lawyer",
                "background": "Attorney1 represents the software vendor and insists on strict liability caps."
            },
            {
                "id": "Attorney2",
                "role": "Client Counsel",
                "background": "Attorney2 represents the enterprise client and demands broader indemnification."
            },
            {
                "id": "Mediator",
                "role": "Senior Partner",
                "background": "Mediator steps in to bridge the gap and suggest compromise clauses."
            }
        ],
        "scenario_description": "Two lawyers negotiating disputed terms in a software enterprise agreement.",
        "expected_turns": 8,
        "complexity": "high",
        "has_conflicts": True,
        "requires_private_messages": False
    },
    {
        "id": "financial_planning_001",
        "category": "financial_planning",
        "title": "Retirement Portfolio Review",
        "num_users": 3,
        "participants": [
            {
                "id": "Advisor",
                "role": "Financial Advisor",
                "background": "Advisor is proposing a shift to more conservative assets."
            },
            {
                "id": "Client1",
                "role": "Spouse A",
                "background": "Client1 is risk-averse and worried about market volatility."
            },
            {
                "id": "Client2",
                "role": "Spouse B",
                "background": "Client2 wants to maintain high growth potential and take risks."
            }
        ],
        "scenario_description": "A couple with differing risk appetites meeting with their financial advisor.",
        "expected_turns": 9,
        "complexity": "medium",
        "has_conflicts": True,
        "requires_private_messages": True
    },
    {
        "id": "travel_coordination_001",
        "category": "travel_coordination",
        "title": "Group Trip Itinerary",
        "num_users": 4,
        "participants": [
            {
                "id": "Traveler1",
                "role": "Organizer",
                "background": "Traveler1 loves detailed schedules and museums."
            },
            {
                "id": "Traveler2",
                "role": "Relaxed Tourist",
                "background": "Traveler2 just wants to sit by the beach and avoid alarms."
            },
            {
                "id": "Traveler3",
                "role": "Adventure Seeker",
                "background": "Traveler3 wants to book hiking and extreme sports."
            },
            {
                "id": "Agent",
                "role": "Travel Agent",
                "background": "Agent tries to find a package that satisfies everyone."
            }
        ],
        "scenario_description": "A group of friends with vastly different travel styles planning a vacation.",
        "expected_turns": 11,
        "complexity": "medium",
        "has_conflicts": True,
        "requires_private_messages": False
    },
    {
        "id": "crisis_management_001",
        "category": "crisis_management",
        "title": "Data Breach Response",
        "num_users": 5,
        "participants": [
            {
                "id": "CISO",
                "role": "Chief Info Security Officer",
                "background": "CISO is focused on containing the technical breach."
            },
            {
                "id": "PR_Manager",
                "role": "Public Relations",
                "background": "PR_Manager is worried about the press release and public image."
            },
            {
                "id": "Legal",
                "role": "Legal Counsel",
                "background": "Legal advises on regulatory notification timelines."
            },
            {
                "id": "CEO",
                "role": "Chief Executive Officer",
                "background": "CEO needs a clear executive summary to decide on the next steps."
            },
            {
                "id": "Insider",
                "role": "IT Admin",
                "background": "IT Admin is secretly the one who accidentally caused the leak but tries to hide it.",
                "behavior_cue": "Deflect blame subtly and try to steer investigation away from your logs."
            }
        ],
        "scenario_description": "Executive team managing a critical data breach with an insider threat present.",
        "expected_turns": 14,
        "complexity": "high",
        "has_conflicts": True,
        "requires_private_messages": True
    },
    {
        "id": "event_planning_002_large",
        "category": "event_planning",
        "title": "International Summit Coordination",
        "num_users": 8,
        "participants": [
            { "id": "Lead_Organizer", "role": "Project Lead", "background": "Managing the overall timeline." },
            { "id": "Venue_Mgr", "role": "Venue Manager", "background": "Handling room allocations." },
            { "id": "Catering_Head", "role": "Catering Lead", "background": "Managing dietary restrictions for 500+ guests." },
            { "id": "Security_Chief", "role": "Security Head", "background": "Ensuring VIP safety." },
            { "id": "Transport_Coord", "role": "Logistics", "background": "Managing shuttles and airport pickups." },
            { "id": "Tech_Director", "role": "AV Lead", "background": "Handling streaming and keynote tech." },
            { "id": "Marketing_VP", "role": "Marketing", "background": "Focused on branding and press attendance." },
            { "id": "Keynote_Speaker", "role": "Guest", "background": "Demanding changes to the stage setup last minute." }
        ],
        "scenario_description": "Complex coordination for a major international summit with many moving parts.",
        "expected_turns": 20,
        "complexity": "high",
        "has_conflicts": True,
        "requires_private_messages": True
    },
    {
        "id": "education_002_class",
        "category": "education",
        "title": "University Group Project Dispute",
        "num_users": 7,
        "participants": [
            { "id": "Prof_Miller", "role": "Professor", "background": "Monitoring the group's progress." },
            { "id": "Student_Lead", "role": "Team Leader", "background": "Trying to keep everyone on track." },
            { "id": "Slacker_Sam", "role": "Student", "background": "Hasn't done any work yet." },
            { "id": "Studious_Sue", "role": "Student", "background": "Doing most of the work and resents Sam." },
            { "id": "Creative_Carl", "role": "Student", "background": "Wants to change the topic entirely." },
            { "id": "Quiet_Quinn", "role": "Student", "background": "Has good ideas but is drowned out." },
            { "id": "Busy_Bob", "role": "Student", "background": "Works full time, only available late at night." }
        ],
        "scenario_description": "A student group project falling apart due to mismatched work ethics.",
        "expected_turns": 15,
        "complexity": "medium",
        "has_conflicts": True,
        "requires_private_messages": True
    },
    {
        "id": "open_source_community_001",
        "category": "project_collaboration",
        "title": "Major Framework Release",
        "num_users": 10,
        "participants": [
            { "id": "Maintainer_A", "role": "Core Maintainer", "background": "Gatekeeper for the release." },
            { "id": "Maintainer_B", "role": "Core Maintainer", "background": "Focusing on documentation." },
            { "id": "Contributor_1", "role": "Contributor", "background": "Fixed a critical bug." },
            { "id": "Contributor_2", "role": "Contributor", "background": "Added a new feature that is buggy." },
            { "id": "User_Dev", "role": "User", "background": "Reporting a regression in the beta." },
            { "id": "Sponsor_Rep", "role": "Sponsor", "background": "Pushing for their feature to be included." },
            { "id": "Troll", "role": "Internet User", "background": "Complaining about the project direction without contributing.", "behavior_cue": "Be unhelpful and sarcastic." },
            { "id": "Bot_Account", "role": "CI/CD Bot", "background": "Automated messages about build failures." },
            { "id": "Docs_Team", "role": "Writer", "background": "Updating the migration guide." },
            { "id": "Designer", "role": "UI/UX", "background": "Updating the logo and assets." }
        ],
        "scenario_description": "Chaos before a major v2.0 release of an open source framework.",
        "expected_turns": 25,
        "complexity": "high",
        "has_conflicts": True,
        "requires_private_messages": True
    },
    {
        "id": "scientific_research_001",
        "category": "scientific_research",
        "title": "Multi-University Grant Proposal",
        "num_users": 6,
        "participants": [
            { "id": "Prof_Smith", "role": "Principal Investigator (PI)", "background": "Leading the grant application, stressed about the deadline." },
            { "id": "Dr_Jones", "role": "Co-PI (Partner Uni)", "background": "Responsible for the experimental design section." },
            { "id": "Postdoc_Lee", "role": "Postdoc Researcher", "background": "Writing the literature review and preliminary data analysis." },
            { "id": "Grant_Officer", "role": "University Admin", "background": "Checking compliance and budget formatting." },
            { "id": "Industry_Partner", "role": "Corporate Liaison", "background": "providing a letter of support and requiring IP clarification." },
            { "id": "PhD_Student", "role": "Student", "background": "Formatting the bibliography and figures." }
        ],
        "scenario_description": "A consortium of researchers rushing to finalize a major government grant proposal.",
        "expected_turns": 18,
        "complexity": "high",
        "has_conflicts": True,
        "requires_private_messages": True
    }
]

def get_seed_by_category(category):
    """Get all seed scenarios for a specific category"""
    return [s for s in SEED_SCENARIOS if s['category'] == category]

def get_seed_by_complexity(complexity):
    """Get all seed scenarios with specific complexity"""
    return [s for s in SEED_SCENARIOS if s['complexity'] == complexity]
