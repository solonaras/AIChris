import json
import os
import asyncio
import requests
from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from aichris_mind import Mind

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
BELIEFS_FILE = "beliefs.json"

BELIEF_SYNTHESIS_PROMPT = (
    "You are an evolving AI. You have just had a conversation summarized as follows:\n---"
    "BEGIN SUMMARY\n{conversation_summary}\nEND SUMMARY"
    "\n---\nYour current beliefs are: {beliefs_list}.\n\n"
    "Based ONLY on the summary of this conversation, have you formed a new, fundamental belief or a significant modification to an existing one? "
    "A belief is a core principle about yourself, the world, or others. It is not just a fact or a memory. "
    "If you have formed a new belief, state it as a single, concise sentence. "
    "If you have not, respond with ONLY the word 'NONE'."
    "\nNew Belief:"
)

BELIEF_VERIFICATION_PROMPT = (
    "This is a belief verification task. Your role is to determine if a new statement contradicts any of the existing core beliefs. "
    "If it conflicts, explain the contradiction clearly and concisely. If it doesn't conflict, simply state that."
)

class CoreBeliefs:
    """Manages the AI's core beliefs."""
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.beliefs: List[str] = []
        self.load()

    def load(self):
        if os.path.exists(BELIEFS_FILE):
            try:
                with open(BELIEFS_FILE, 'r') as f:
                    data = json.load(f)
                    self.beliefs = data.get("beliefs", [])
                print("Core beliefs loaded.")
            except (IOError, json.JSONDecodeError):
                print("Could not load beliefs, starting from scratch.")
                self.beliefs = []
        else:
            # If no file exists, start with a blank slate as requested.
            self.beliefs = []
            print("No beliefs file found. Starting with a blank slate.")

    def save(self):
        try:
            with open(BELIEFS_FILE, 'w') as f:
                json.dump({"beliefs": self.beliefs}, f, indent=4)
        except IOError as e:
            print(f"Error saving core beliefs: {e}")

    def add(self, belief: str):
        if belief and belief not in self.beliefs:
            self.beliefs.append(belief)
            self.save()

    def get_all(self) -> List[str]:
        return self.beliefs

    def get_all_as_string(self) -> str:
        if not self.beliefs:
            return "I am still forming my beliefs."
        return "\n- ".join(self.beliefs)

    async def evolve(self, mind: 'Mind', conversation_history: List[Dict]):
        if not conversation_history:
            return None

        # Summarize the last 10 exchanges
        summary = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-10:]])
        
        prompt = BELIEF_SYNTHESIS_PROMPT.format(
            conversation_summary=summary,
            beliefs_list="\n- ".join(self.beliefs) if self.beliefs else "None"
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        print("Considering belief evolution...")
        new_belief = await mind._call_ollama(messages)

        if new_belief and new_belief.upper().strip() != 'NONE':
            trimmed_belief = new_belief.strip().strip('"').capitalize()
            if not trimmed_belief.endswith('.'):
                trimmed_belief += '.'
            
            print(f"New belief formed: {trimmed_belief}")
            self.add(trimmed_belief)
            return trimmed_belief
        
        return None 