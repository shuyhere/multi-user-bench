from typing import Dict, List, Tuple, Any, Set
from .base_env import BaseEnv
from ..core.user import User
from ..core.types import Action, Observation

class MeetingSchedulingEnv(BaseEnv):
    """
    Scenario 2: Multi-User Meeting Scheduling.
    
    Users have private availability.
    The agent must coordinate to find a common meeting time.
    """

    def __init__(self, users: List[User], availabilities: Dict[str, List[int]]):
        super().__init__(users)
        self.availabilities = availabilities # user_id -> list of available time slots (integers)
        self.proposed_time: int = -1
        self.confirmed_users: Set[str] = set()

    def step(self, action: Action) -> Tuple[Dict[str, Observation], float, bool, Dict[str, Any]]:
        observations = {}
        reward = 0.0
        done = False
        info = {}

        if action.name == "query_availability":
            target_user_id = action.arguments["target_user_id"]
            if target_user_id in self.users:
                # In a real POMDP, this might be noisy or partial.
                # Here we return the full availability for simplicity, or a subset.
                avail = self.availabilities.get(target_user_id, [])
                observations["agent"] = Observation( # Agent observes the result
                    content=f"User {target_user_id} is available at: {avail}"
                )
                # The user also receives a message that they were queried? 
                # For now, let's assume agent gets direct info or via a message.
                # Let's model it as agent sending a message and user replying.
                # But to fit the step structure:
                observations[target_user_id] = Observation(
                    content="The agent asked for your availability."
                )

        elif action.name == "propose_time":
            time_slot = action.arguments["time_slot"]
            self.proposed_time = time_slot
            self.confirmed_users = set()
            # Broadcast proposal
            for uid in self.users:
                observations[uid] = Observation(
                    content=f"Agent proposed meeting at time {time_slot}. Please confirm or reject."
                )

        elif action.name == "finalize_schedule":
            # Agent decides to finalize the meeting at the proposed time
            done = True
            # Calculate reward: 
            # Global Utility = sum(u_i)
            # u_i = 1 (if meeting scheduled in available slot) - lambda * delay
            
            all_available = True
            if self.proposed_time == -1:
                all_available = False
            else:
                for uid, slots in self.availabilities.items():
                    if self.proposed_time not in slots:
                        all_available = False
                        break
            
            if all_available:
                # Success!
                for uid, user in self.users.items():
                    # Delay is number of steps taken.
                    # We can normalize or just use raw steps.
                    delay_penalty = user.lambda_val * self.time_step * 0.1 # Scaling factor
                    reward += (10.0 - delay_penalty) # Base reward 10
                info["status"] = "success"
            else:
                # Failure
                reward = -10.0 # Penalty for failure
                info["status"] = "failure"

        self.time_step += 1
        return observations, reward, done, info

    def reset(self) -> Dict[str, Observation]:
        self.proposed_time = -1
        self.confirmed_users = set()
        observations = {}
        for uid in self.users:
            observations[uid] = Observation(
                content=f"Please schedule a meeting. Your availability is {self.availabilities.get(uid)}."
            )
        return observations

    def render(self):
        print(f"Time Step: {self.time_step}")
        print(f"Proposed Time: {self.proposed_time}")
        print(f"Availabilities: {self.availabilities}")
