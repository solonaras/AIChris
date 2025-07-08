import json
import os
from typing import Dict

TRUST_STATE_FILE = "trust_state.json"

class TrustEngine:
    """Manages trust levels with different users."""
    def __init__(self):
        self.trust_levels: Dict[str, float] = {}
        self.load_state()

    def get_trust(self, user_id: str) -> float:
        """Gets the trust level for a specific user."""
        return self.trust_levels.get(user_id, 0.5)  # Default to a neutral trust level

    def get_trust_level(self, user_id: str) -> float:
        """Alias for get_trust for compatibility."""
        return self.get_trust(user_id)

    def _adjust_trust(self, user_id: str, amount: float):
        """Adjusts the trust level for a user, keeping it between 0 and 1."""
        current_trust = self.get_trust(user_id)
        new_trust = max(0, min(1, current_trust + amount))
        self.trust_levels[user_id] = new_trust
        print(f"Trust for {user_id} adjusted by {amount}. New level: {new_trust:.2f}")

    def positive_interaction(self, user_id: str):
        """Increases trust after a positive interaction."""
        self._adjust_trust(user_id, 0.05)

    def negative_interaction(self, user_id: str):
        """Decreases trust after a negative interaction."""
        self._adjust_trust(user_id, -0.1)

    def get_trust_description(self, user_id: str) -> str:
        """Returns a human-readable description of the trust level."""
        trust = self.get_trust(user_id)
        if trust > 0.8:
            return "Completely Trusted"
        elif trust > 0.6:
            return "Trusted Ally"
        elif trust > 0.4:
            return "Neutral"
        elif trust > 0.2:
            return "Wary"
        else:
            return "Distrusted"

    def save_state(self):
        """Saves the current trust levels to a file."""
        try:
            with open(TRUST_STATE_FILE, 'w') as f:
                json.dump(self.trust_levels, f, indent=4)
        except Exception as e:
            print(f"Error saving trust state: {e}")

    def load_state(self):
        """Loads trust levels from a file."""
        if os.path.exists(TRUST_STATE_FILE):
            try:
                with open(TRUST_STATE_FILE, 'r') as f:
                    self.trust_levels = json.load(f)
                    print("Trust engine state loaded.")
            except Exception as e:
                print(f"Error loading trust state: {e}") 