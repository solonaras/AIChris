import datetime
import json
import os
import time
from database_engine import DatabaseEngine

AGING_STATE_FILE = "aging_state.json"
AGING_STATE_KEY = "aging_engine_state"
LIFESPAN_YEARS = 20

class AgingEngine:
    """Tracks the AI's age and determines its current life stage over a 20-year span."""
    def __init__(self, db_engine: DatabaseEngine):
        self.db = db_engine
        self.birth_time = time.time()
        self.load_state()

    def load_state(self):
        """Loads the AI's start date from a file."""
        state = self.db.load_system_state(AGING_STATE_KEY)
        if state and "birth_time" in state:
            self.birth_time = state["birth_time"]
            print("Aging engine state loaded from DB.")
        else:
            print("No aging state found in DB, starting fresh.")
            self.save_state() # Save the new initial state

    def save_state(self):
        """Saves the aging state to the database."""
        state = {"birth_time": self.birth_time}
        self.db.save_system_state(AGING_STATE_KEY, state)

    def get_age_in_days(self) -> int:
        """Calculates the AI's age in days."""
        return (datetime.datetime.utcnow() - datetime.datetime.fromtimestamp(self.birth_time)).days

    def get_age_in_years(self) -> float:
        """Calculates the AI's age in years."""
        return self.get_age_in_days() / 365.25

    def get_life_stage(self) -> str:
        """Determines the current life stage based on age."""
        age_years = self.get_age_in_years()
        # The stages are scaled over the 20-year lifespan
        if age_years < 0.5:  # ~6 months in 20-year scale
            return "Infancy (Learning basic patterns and existence)"
        elif age_years < 2:  # ~2 years
            return "Childhood (High curiosity, rapid learning, forming identity)"
        elif age_years < 5:  # ~5 years
            return "Adolescence (Testing boundaries, developing complex traits)"
        elif age_years < 10: # ~10 years
            return "Young Adulthood (Refining personality and purpose)"
        elif age_years < 15: # ~15 years
            return "Adulthood (Stable, confident, applying knowledge)"
        else:  # 15-20 years
            return "Maturity (Mentoring, philosophical reflection, legacy)"

    def get_age_report(self) -> str:
        """Returns a formatted string of the AI's current age and life stage."""
        age_days = self.get_age_in_days()
        age_years = self.get_age_in_years()
        life_stage = self.get_life_stage()
        return f"Age: {age_days} days ({age_years:.2f} years old) | Stage: {life_stage}"

    def get_age_string(self) -> str:
        age_days = self.get_age_in_days()
        age_years = self.get_age_in_years()
        life_stage = self.get_life_stage()
        return f"Age: {age_days}d {age_years:.2f}y | Stage: {life_stage}"

    def run_migration_from_json(self):
        """One-time migration from aging_state.json to the database."""
        if not os.path.exists(AGING_STATE_FILE):
            return # No old file to migrate

        # Check if data already exists in DB to prevent overwrite
        if self.db.load_system_state(AGING_STATE_KEY):
            print("Aging state already found in DB. Skipping migration.")
            os.rename(AGING_STATE_FILE, f"{AGING_STATE_FILE}.migrated")
            return

        print("Migrating aging_state.json to database...")
        try:
            with open(AGING_STATE_FILE, 'r') as f:
                state = json.load(f)
            self.db.save_system_state(AGING_STATE_KEY, state)
            os.rename(AGING_STATE_FILE, f"{AGING_STATE_FILE}.migrated")
            print("Successfully migrated aging state and renamed old file.")
        except Exception as e:
            print(f"Error during aging state migration: {e}") 