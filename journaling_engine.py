import json
import os
import time
from typing import List, Dict, Any

JOURNAL_FILE = "aichris_journal.jsonl"

class JournalingEngine:
    """Handles the AI's long-term, structured journaling."""

    def add_entry(self, entry_type: str, content: str, metadata: Dict[str, Any] = None):
        """
        Adds a new entry to the journal.
        
        Args:
            entry_type: The type of entry (e.g., 'reflection', 'dream', 'goal_completed').
            content: The main text of the journal entry.
            metadata: Any additional data to store with the entry.
        """
        if metadata is None:
            metadata = {}
            
        entry = {
            "timestamp": time.time(),
            "entry_type": entry_type,
            "content": content,
            "metadata": metadata
        }
        
        try:
            with open(JOURNAL_FILE, 'a') as f:
                f.write(json.dumps(entry) + '\n')
            print(f"Journal entry added: {entry_type} - {content[:50]}...")
        except Exception as e:
            print(f"Error writing to journal: {e}")

    def get_recent_entries(self, count: int = 5) -> List[Dict]:
        """Retrieves the most recent journal entries."""
        if not os.path.exists(JOURNAL_FILE):
            return []
        
        try:
            with open(JOURNAL_FILE, 'r') as f:
                lines = f.readlines()
            
            recent_lines = lines[-count:]
            return [json.loads(line) for line in recent_lines]
        except Exception as e:
            print(f"Error reading journal: {e}")
            return [] 