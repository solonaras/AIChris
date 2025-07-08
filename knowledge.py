import json
import os
import asyncio
import requests
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from aichris_mind import Mind

KNOWLEDGE_FILE = "knowledge_base.json"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")

LEARNING_PROMPT = (
    "This is a knowledge extraction task. Analyze the following conversation transcript and identify any new, factual information that should be saved to a knowledge base. "
    "Focus on concrete facts, definitions, and key details about people, places, concepts, or events. Ignore opinions, questions, and conversational filler. "
    "--- CURRENT KNOWLEDGE BASE ---\n{knowledge_base}\n\n"
    "--- RECENT CONVERSATION ---\n{conversation_summary}\n\n"
    "--- NEW KNOWLEDGE (JSON format) ---\n"
    "Provide the output as a JSON object, where each key is a new fact and the value is its description. "
    "If no new knowledge is found, return an empty JSON object {}."
)

class KnowledgeBase:
    """Manages the AI's knowledge base."""
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.facts: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Loads knowledge from a JSON file."""
        if os.path.exists(KNOWLEDGE_FILE):
            try:
                with open(KNOWLEDGE_FILE, 'r') as f:
                    self.facts = json.load(f)
                print("Knowledge base loaded.")
            except (IOError, json.JSONDecodeError):
                self.initialize_default()
        else:
            self.initialize_default()

    def initialize_default(self):
        """Initializes with some default facts."""
        self.facts = {
            "self": {
                "name": "AI Chris",
                "purpose": "to be a helpful and engaging conversationalist, learning and growing through interaction."
            },
            "others": {
                "solonaras": "The creator of the AI Chris project."
            }
        }
        print("Initialized with default knowledge base.")
        self.save()

    def save(self):
        """Saves the current knowledge base to a JSON file."""
        try:
            with open(KNOWLEDGE_FILE, 'w') as f:
                json.dump(self.facts, f, indent=4)
        except IOError as e:
            print(f"Error saving knowledge base: {e}")

    async def extract_and_learn(self, mind: 'Mind', conversation_history: List[Dict]):
        """Analyzes a conversation and adds new facts to the knowledge base."""
        summary = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-10:]])
        
        prompt = LEARNING_PROMPT.format(
            knowledge_base=self.get_all_as_string(),
            conversation_summary=summary
        )
        
        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json"
        }
        
        print("Extracting new knowledge from conversation...")
        response = await mind._call_ollama(payload)

        try:
            new_facts = json.loads(response)
            if new_facts:
                print(f"Learned new facts: {new_facts}")
                for key, value in new_facts.items():
                    # For simplicity, we add new facts to a 'general' category.
                    # A more sophisticated system could categorize them.
                    self.set("general", key, value)
                self.save() # Save after updating
        except json.JSONDecodeError:
            print(f"Could not decode learned facts from LLM response: {response}")

    def get(self, key: str) -> Any:
        """Retrieves a fact from the knowledge base."""
        return self.facts.get(key)

    def set(self, category: str, key: str, value: Any):
        """Sets or updates a fact in the knowledge base."""
        if category not in self.facts:
            self.facts[category] = {}
        self.facts[category][key] = value
        self.save()

    def get_agent_statement(self) -> str:
        """Synthesizes the core 'self' facts into a single identity statement."""
        self_facts = self.facts.get("self", {})
        name = self_facts.get("name", "an AI")
        purpose = self_facts.get("purpose", "to assist users")
        creator = self.facts.get("others", {}).get("solonaras", "my creator")
        
        return f"I am {name}, an AI created by {creator}. My purpose is {purpose}."

    def get_all_as_string(self) -> str:
        """Returns the entire knowledge base as a formatted string."""
        output = []
        for category, items in self.facts.items():
            output.append(f"### {category.capitalize()}")
            for key, value in items.items():
                output.append(f"- **{key}:** {value}")
        return "\n".join(output) 