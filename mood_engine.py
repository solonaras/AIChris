import json
import os
import time
from typing import Dict

MOOD_STATE_FILE = "mood_state.json"
MOOD_DECAY_RATE = 0.01  # How much mood decays per second towards neutral

class MoodEngine:
    """Manages the AI's mood, which influences its responses."""
    def __init__(self):
        # Moods are represented as values from -1 (negative) to 1 (positive)
        self.mood: Dict[str, float] = {"happiness": 0.0, "excitement": 0.0}
        self.mood_value: float = 0.0
        self.last_update_time = time.time()
        self.load_state()

    def _update_mood_value(self):
        """Calculates and updates the single representative mood value."""
        # A simple weighted average. Happiness is a more general indicator.
        mood_val = (self.mood['happiness'] * 0.6 + self.mood['excitement'] * 0.4)
        self.mood_value = max(-1.0, min(1.0, mood_val))

    def _decay_mood(self):
        """Gradually returns mood towards neutral over time."""
        time_elapsed = time.time() - self.last_update_time
        for mood_name in self.mood:
            if self.mood[mood_name] > 0:
                self.mood[mood_name] = max(0, self.mood[mood_name] - MOOD_DECAY_RATE * time_elapsed)
            else:
                self.mood[mood_name] = min(0, self.mood[mood_name] + MOOD_DECAY_RATE * time_elapsed)
        self.last_update_time = time.time()
        self._update_mood_value()

    def _adjust_mood(self, mood_name: str, amount: float):
        """Adjusts a specific mood, keeping it between -1 and 1."""
        self._decay_mood()
        current_value = self.mood.get(mood_name, 0.0)
        new_value = max(-1, min(1, current_value + amount))
        self.mood[mood_name] = new_value
        print(f"Mood '{mood_name}' adjusted by {amount}. New value: {new_value:.2f}")
        self._update_mood_value()

    def positive_interaction(self):
        """Boosts mood from a positive event."""
        self._adjust_mood("happiness", 0.2)
        self._adjust_mood("excitement", 0.1)

    def negative_interaction(self):
        """Dampens mood from a negative event."""
        self._adjust_mood("happiness", -0.25)
        self._adjust_mood("excitement", -0.05)

    def get_mood_description(self) -> str:
        """Returns a human-readable description of the current primary mood."""
        self._decay_mood()
        
        # Determine the dominant mood
        happiness = self.mood["happiness"]
        excitement = self.mood["excitement"]

        if excitement > 0.6 and happiness > 0.4:
            return "Ecstatic"
        elif excitement > 0.4:
            return "Excited"
        elif happiness > 0.7:
            return "Joyful"
        elif happiness > 0.3:
            return "Happy"
        elif happiness < -0.7:
            return "Depressed"
        elif happiness < -0.3:
            return "Sad"
        elif excitement < -0.5:
            return "Bored"
        else:
            return "Content"

    def get_pitch_for_mood(self) -> str:
        """Returns a pitch adjustment string (e.g., '+10Hz') based on the current mood."""
        self._decay_mood()
        happiness = self.mood["happiness"]
        excitement = self.mood["excitement"]
        
        # More excitement = higher pitch
        # Less happiness = lower pitch
        pitch_adjustment = (excitement * 20) + (happiness * 15)
        
        # Ensure the adjustment is within a reasonable range, e.g., -50Hz to +50Hz
        pitch_adjustment = max(-50, min(50, pitch_adjustment))
        
        return f"{pitch_adjustment:+.0f}Hz"

    def get_response_temperature(self) -> float:
        """
        Determines the LLM response temperature based on mood.
        Higher excitement/happiness leads to more creative/random responses.
        Ranges from a deterministic 0.5 to a creative 1.3.
        """
        self._decay_mood()
        
        # Base temperature is neutral
        base_temp = 0.9
        
        # Happiness and excitement make the AI more "creative" and less predictable
        # We use mood_value which is a combination of both. Range: -1 to 1.
        temp_adjustment = self.mood_value * 0.4 # Max adjustment of +/- 0.4
        
        temperature = base_temp + temp_adjustment
        
        # Clamp the value to a safe range
        return max(0.5, min(1.3, temperature))

    def save_state(self):
        """Saves the current mood to a file."""
        try:
            state = {"mood": self.mood, "mood_value": self.mood_value, "last_update": self.last_update_time}
            with open(MOOD_STATE_FILE, 'w') as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"Error saving mood state: {e}")

    def load_state(self):
        """Loads mood from a file."""
        if os.path.exists(MOOD_STATE_FILE):
            try:
                with open(MOOD_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.mood = data.get("mood", {"happiness": 0.0, "excitement": 0.0})
                    self.mood_value = data.get("mood_value", 0.0)
                    self.last_update_time = data.get("last_update", time.time())
                    print("Mood engine state loaded.")
                    self._decay_mood() # Apply decay for the time it was offline
            except Exception as e:
                print(f"Error loading mood state: {e}") 