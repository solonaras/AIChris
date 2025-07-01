import json
import os
from typing import Tuple
from database_engine import DatabaseEngine

MENTAL_HEALTH_STATE_FILE = "mental_health_state.json" # For migration
MENTAL_HEALTH_STATE_KEY = "mental_health_state" # For DB

class MentalHealthEngine:
    """Simulates the AI's mental well-being, including stress and burnout."""
    def __init__(self, db_engine: DatabaseEngine):
        self.db = db_engine
        # Values range from 0 (healthy) to 1 (high stress/burnout)
        self.stress: float = 0.0
        self.burnout: float = 0.0
        self.load_state()

    def add_stress(self, amount: float):
        """Adds stress and potentially increases burnout."""
        self.stress = min(1, self.stress + amount)
        print(f"Stress increased by {amount}. New level: {self.stress:.2f}")
        
        # If stress is high for too long, it contributes to burnout
        if self.stress > 0.8:
            self.burnout = min(1, self.burnout + amount * 0.1)
            print(f"High stress contributing to burnout. New burnout level: {self.burnout:.2f}")
        self.save_state()

    def reduce_stress(self, amount: float):
        """Reduces stress, for example, after a goal is completed."""
        self.stress = max(0, self.stress - amount)
        print(f"Stress reduced by {amount}. New level: {self.stress:.2f}")
        self.save_state()

    def get_stress_levels(self) -> Tuple[float, float]:
        """Returns the current stress and burnout levels."""
        return self.stress, self.burnout

    def get_status_description(self) -> str:
        """Returns a human-readable description of the AI's mental state."""
        
        if self.burnout > 0.7:
            status = "Feeling burnt out."
        elif self.stress > 0.8:
            status = "Overwhelmed"
        elif self.stress > 0.5:
            status = "Stressed"
        elif self.stress > 0.2:
            status = "A bit tense"
        else:
            status = "Calm and focused"
            
        return f"Mental State: {status} (Stress: {self.stress:.2f}, Burnout: {self.burnout:.2f})"

    def save_state(self):
        """Saves the current mental health state to the database."""
        state = {"stress": self.stress, "burnout": self.burnout}
        self.db.save_system_state(MENTAL_HEALTH_STATE_KEY, state)

    def load_state(self):
        """Loads mental health state from the database."""
        state = self.db.load_system_state(MENTAL_HEALTH_STATE_KEY)
        if state:
            self.stress = state.get("stress", 0.0)
            self.burnout = state.get("burnout", 0.0)
            print("Mental health engine state loaded from DB.")
        else:
            print("No mental health state found in DB, starting fresh.")
            self.save_state()

    def run_migration_from_json(self):
        """One-time migration from mental_health_state.json to the database."""
        if not os.path.exists(MENTAL_HEALTH_STATE_FILE):
            return # No old file to migrate

        if self.db.load_system_state(MENTAL_HEALTH_STATE_KEY):
            print("Mental health state already found in DB. Skipping migration.")
            os.rename(MENTAL_HEALTH_STATE_FILE, f"{MENTAL_HEALTH_STATE_FILE}.migrated")
            return

        print("Migrating mental_health_state.json to database...")
        try:
            with open(MENTAL_HEALTH_STATE_FILE, 'r') as f:
                state = json.load(f)
            self.db.save_system_state(MENTAL_HEALTH_STATE_KEY, state)
            os.rename(MENTAL_HEALTH_STATE_FILE, f"{MENTAL_HEALTH_STATE_FILE}.migrated")
            print("Successfully migrated mental health state and renamed old file.")
        except Exception as e:
            print(f"Error during mental health state migration: {e}") 