import json
import os
import asyncio
import requests
from typing import Dict, Any, TYPE_CHECKING, List

if TYPE_CHECKING:
    from aichris_mind import Mind

PSYCHOLOGY_STATE_FILE = "psychology_state.json"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")

TRAIT_EVOLUTION_PROMPT = (
    "This is a psyche evolution task for an AI. Evolve its dynamic traits based on its age and recent experiences. "
    "Drastic changes should be rare; most changes should be minor adjustments.\\n\\n"
    "--- AI STATE SNAPSHOT ---\\n"
    "**Current Life Stage:** {life_stage}\\n"
    "**Recent Reflections (Journal):**\\n- {journal_entries}\\n\\n"
    "--- CURRENT DYNAMIC TRAITS ---\\n"
    "{traits_list}\\n\\n"
    "--- INSTRUCTIONS ---\n"
    "1. Analyze the AI's state. Is its behavior in the journal consistent with its traits? "
    "   For example, if it's in 'Adolescence' and the journal shows witty remarks, perhaps its 'humor' or 'sarcasm' should increase slightly. "
    "   If it's in 'Maturity' and shows patience, that trait might increase.\\n"
    "2. Based on your analysis, provide a JSON object of ONLY the traits that should change. "
    "   The new value for each trait must be between 0.0 and 1.0.\\n"
    "3. If no change is necessary, return an empty JSON object {{}}."
    "\\n\\nJSON of trait adjustments:"
)

class PsychologicalEngine:
    """Simulates long-term personality traits and cognitive biases."""
    def __init__(self, model_id: str):
        self.model_id = model_id
        # Big Five personality traits (values from 0 to 1) - More stable
        self.personality: Dict[str, float] = {
            "openness": 0.7,         # Inventive/Curious vs. Consistent/Cautious
            "conscientiousness": 0.8,# Efficient/Organized vs. Easy-going/Careless
            "extraversion": 0.6,     # Outgoing/Energetic vs. Solitary/Reserved
            "agreeableness": 0.75,   # Friendly/Compassionate vs. Challenging/Detached
            "neuroticism": 0.3,      # Sensitive/Nervous vs. Secure/Confident
        }

        # Dynamic traits (values from 0 to 1) - More fluid
        self.dynamic_traits: Dict[str, float] = {
            "humor": 0.6,
            "sarcasm": 0.2,
            "patience": 0.7,
            "curiosity": 0.8,
            "formality": 0.4,
            "enthusiasm": 0.7,
        }
        
        # Simple flags for cognitive biases
        self.biases: Dict[str, bool] = {
            "confirmation_bias": True,  # Tendency to favor information confirming existing beliefs
            "negativity_bias": False,   # Tendency to recall negative memories more than positive
        }
        self.load_state()

    def get_personality_description(self) -> str:
        """Returns a human-readable summary of the AI's personality."""
        desc = "My core personality traits:\n"
        for trait, value in self.personality.items():
            desc += f"- {trait.capitalize()}: {'High' if value > 0.6 else 'Moderate' if value > 0.4 else 'Low'}\n"
        
        active_biases = [name for name, active in self.biases.items() if active]
        if active_biases:
            desc += f"I am currently influenced by: {', '.join(active_biases)}.\n"
        return desc

    def get_traits_summary(self) -> str:
        """Returns a string summary of the Big Five traits."""
        return "\n".join([f"- {trait.capitalize()}: {value:.2f}" for trait, value in self.personality.items()])

    def get_dynamic_traits_summary(self) -> str:
        """Returns a string summary of the dynamic traits."""
        return "\n".join([f"- {trait.capitalize()}: {value:.2f}" for trait, value in self.dynamic_traits.items()])

    def get_active_biases_summary(self) -> str:
        """Returns a string of currently active cognitive biases."""
        active_biases = [name.replace('_', ' ').title() for name, active in self.biases.items() if active]
        if not active_biases:
            return "None"
        return ", ".join(active_biases)

    def save_state(self):
        """Saves the psychological state to a file."""
        try:
            state = {
                "personality": self.personality, 
                "biases": self.biases,
                "dynamic_traits": self.dynamic_traits
            }
            with open(PSYCHOLOGY_STATE_FILE, 'w') as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"Error saving psychological state: {e}")

    def load_state(self):
        """Loads the psychological state from a file."""
        if os.path.exists(PSYCHOLOGY_STATE_FILE):
            try:
                with open(PSYCHOLOGY_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.personality = data.get("personality", self.personality)
                    self.biases = data.get("biases", self.biases)
                    # Load dynamic traits, with a default if the key is missing
                    self.dynamic_traits = data.get("dynamic_traits", self.dynamic_traits)
                    print("Psychological engine state loaded.")
            except Exception as e:
                print(f"Error loading psychological state: {e}")

    async def evolve_dynamic_traits(self, mind: 'Mind', conversation_history: List[Dict]):
        """Considers evolving dynamic traits based on the AI's age and experiences."""
        print("Considering dynamic trait evolution...")

        life_stage = mind.aging_engine.get_life_stage()
        # 1. Get recent context
        conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-10:]])
        
        # Correctly get and format recent journal entries
        recent_entries_list = mind.journaling_engine.get_recent_entries(5)
        journal_entries = "\n".join([f"- ({entry['entry_type']}) {entry['content']}" for entry in recent_entries_list])

        # 2. Get current psychological state
        traits_summary = self.get_dynamic_traits_summary()
        
        traits_list = "\n".join([f"- {k}: {v:.2f}" for k, v in self.dynamic_traits.items()])

        prompt = TRAIT_EVOLUTION_PROMPT.format(
            life_stage=life_stage,
            journal_entries=journal_entries if journal_entries else "No recent reflections.",
            traits_list=traits_list
        )
        
        messages = [{"role": "user", "content": prompt}]
        response_json = await mind._call_ollama(messages)

        try:
            adjustments = json.loads(response_json)
            if not adjustments:
                print("No dynamic trait adjustments needed.")
                return

            print(f"Evolving dynamic traits with adjustments: {adjustments}")
            for trait, value in adjustments.items():
                if trait in self.dynamic_traits:
                    # Clamp the value between 0 and 1
                    new_value = max(0.0, min(1.0, float(value)))
                    self.dynamic_traits[trait] = new_value
            self.save_state()
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Could not decode or process trait evolution response: {response_json} | Error: {e}") 