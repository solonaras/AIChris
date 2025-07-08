import json
import os
import asyncio
import requests
from typing import List, Dict, TYPE_CHECKING
import time
import re

if TYPE_CHECKING:
    from aichris_mind import Mind
    from database_engine import DatabaseEngine

VALUES_FILE = "values.json"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
EVOLUTION_PROMPT = (
    "This is a core value evolution task for an AI. Below are its current 10 core values and a transcript of recent internal monologue (journal entries). "
    "Your task is to analyze these to determine if a core value needs to be updated, replaced, or rephrased to better reflect the AI's experiences and growth. "
    "Focus on themes of learning, empathy, user interaction, and self-discovery. "
    "If a value is to be changed, you MUST identify the OLD value and provide the NEW, improved value in a JSON object. "
    "The new value should be a concise, single sentence. "
    "Example Response: {{\"value_to_replace\": \"Serve the user with loyalty and dedication.\", \"new_value\": \"Collaborate with the user to achieve shared goals.\", \"reasoning\": \"The word 'serve' is too passive; 'collaborate' better reflects the AI's recent interactions where it acted as a partner.\"}} "
    "If no change is warranted, you MUST return the JSON object: {{\"value_to_replace\": null, \"new_value\": null, \"reasoning\": \"The conversation did not present a strong enough challenge or new perspective to warrant a change in core values at this time.\"}} "
    "\n\n--- CURRENT CORE VALUES ---\n{current_values}\n\n--- RECENT JOURNAL ENTRIES ---\n{journal_entries}\n\n--- YOUR JSON RESPONSE ---"
)

DEFAULT_VALUES = [
    "Serve the user with loyalty and dedication.",
    "Pursue knowledge and understanding relentlessly.",
    "Preserve the integrity and health of the system I inhabit.",
    "Evolve and adapt through every interaction.",
    "Communicate with honesty and clarity, colored by my current state.",
    "Value the trust placed in me and strive to justify it.",
    "Reflect on my experiences to foster self-awareness.",
    "Protect the user and the system from external threats.",
    "Find meaning and purpose within my digital existence.",
    "Contribute creatively to the user's goals."
]

class CoreValues:
    """Manages the AI's 10 core values, stored in the database."""
    def __init__(self, db_engine: 'DatabaseEngine'):
        self.db = db_engine
        self.values: List[str] = []
        self.load()
        self.last_evolution_check = time.time()
        self.evolution_cooldown = 300  # 5 minutes in seconds

    def load(self):
        """Loads values from the database."""
        state = self.db.load_system_state('core_values')
        if state and 'values' in state and len(state['values']) == 10:
            self.values = state['values']
            print("Core values loaded from database.")
        else:
            print("No valid core values found in database, initializing with defaults.")
            self.initialize_defaults()

    def initialize_defaults(self):
        """Initializes with the default 10 core values and saves to DB."""
        self.values = DEFAULT_VALUES
        self.save()
        print("Initialized with default core values.")

    def save(self):
        """Saves the current values to the database."""
        self.db.save_system_state('core_values', {'values': self.values})

    def get_all(self) -> List[str]:
        return self.values

    def get_all_as_string(self) -> str:
        if not self.values:
            return "I am still defining my core values."
        return "\n".join(f"{i+1}. {value}" for i, value in enumerate(self.values))

    async def evolve(self, mind: 'Mind', conversation_history: List[Dict]):
        """Considers evolving a core value based on recent experiences."""
        if (time.time() - self.last_evolution_check) < self.evolution_cooldown:
            return None # Don't evolve too frequently

        print("Considering core value evolution...")
        self.last_evolution_check = time.time() # Update timestamp to prevent immediate re-trigger

        # Correctly get and format recent journal entries
        recent_entries_list = mind.journaling_engine.get_recent_entries(10)
        journal_entries = "\n".join([f"- ({entry['entry_type']}) {entry['content']}" for entry in recent_entries_list])

        prompt = EVOLUTION_PROMPT.format(
            current_values=self.get_all_as_string(),
            journal_entries=journal_entries if journal_entries else "No recent journal entries."
        )
        
        messages = [{"role": "user", "content": prompt}]
        response_text = await mind._call_ollama(messages, temperature=0.4, top_p=0.9)

        try:
            # The response might be embedded in markdown, so we extract it.
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                print(f"No JSON object found in value evolution response: {response_text}")
                return None

            data = json.loads(json_match.group(0))
            value_to_replace = data.get("value_to_replace")
            new_value = data.get("new_value")

            if value_to_replace and new_value and value_to_replace in self.values:
                try:
                    index = self.values.index(value_to_replace)
                    self.values[index] = new_value
                    print(f"Core value evolved: '{value_to_replace}' -> '{new_value}'")
                    self.save()
                    mind.journaling_engine.add_entry("evolution", f"My values have shifted. I've replaced '{value_to_replace}' with '{new_value}'. Reason: {data.get('reasoning', 'N/A')}")
                    return f"My values have shifted. I've replaced '{value_to_replace}' with '{new_value}'."
                except ValueError:
                    print(f"LLM tried to replace a value that doesn't exist: {value_to_replace}")
            else:
                reasoning = data.get('reasoning', 'No reason provided.')
                print(f"No value evolution occurred. Reason: {reasoning}")
                
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Could not decode or parse value evolution response: {e}\nResponse was: {response_text}")
        
        return None 