import json
import os
from typing import List, Dict
import time

GOALS_STATE_FILE = "goals_state.json"

class GoalsEngine:
    """Manages the AI's short-term and long-term goals."""
    def __init__(self):
        self.goals: List[Dict] = []
        self.load_state()

    def add_goal(self, description: str, priority: int = 5):
        """Adds a new goal to the list."""
        new_goal = {
            "description": description,
            "priority": priority,
            "completed": False,
            "timestamp": time.time()
        }
        self.goals.append(new_goal)
        print(f"New goal added: '{description}' with priority {priority}")
        self.save_state()

    def complete_goal(self, description: str):
        """Marks a goal as completed."""
        for goal in self.goals:
            if goal["description"].lower() == description.lower() and not goal["completed"]:
                goal["completed"] = True
                print(f"Goal completed: '{goal['description']}'")
                self.save_state()
                return
        print(f"Could not find active goal: '{description}'")

    def get_active_goals(self) -> List[Dict]:
        """Returns a list of all non-completed goals, sorted by priority."""
        active = [goal for goal in self.goals if not goal["completed"]]
        return sorted(active, key=lambda x: x['priority'])

    def get_active_goals_string(self) -> str:
        """Returns a simple, formatted string of top active goals."""
        active_goals = self.get_active_goals()
        if not active_goals:
            return "No active goals."
        # Return top 3 goals as a simple list
        return "\n".join([f"- {goal['description']}" for goal in active_goals[:3]])

    def get_goals_description(self) -> str:
        """Returns a formatted string of the top active goals."""
        active_goals = self.get_active_goals()
        if not active_goals:
            return "No active goals right now. I'm open to suggestions!"
        
        description = "My current objectives are:\n"
        # Show top 3 goals
        for goal in active_goals[:3]:
            description += f"- {goal['description']} (Priority: {goal['priority']})\n"
        return description

    def save_state(self):
        """Saves the current goals to a file."""
        try:
            with open(GOALS_STATE_FILE, 'w') as f:
                json.dump(self.goals, f, indent=4)
        except Exception as e:
            print(f"Error saving goals state: {e}")

    def load_state(self):
        """Loads goals from a file."""
        if os.path.exists(GOALS_STATE_FILE):
            try:
                with open(GOALS_STATE_FILE, 'r') as f:
                    self.goals = json.load(f)
                    print("Goals engine state loaded.")
            except Exception as e:
                print(f"Error loading goals state: {e}") 