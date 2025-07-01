import json
import os
import time
import asyncio
from typing import Dict, Any, List, TYPE_CHECKING
from database_engine import DatabaseEngine

if TYPE_CHECKING:
    from aichris_mind import Mind

# This constant is no longer the primary source of truth, but can be used for migration.
USER_PROFILES_FILE = "user_profiles.json"

SUMMARY_UPDATE_PROMPT = (
    "This is a memory consolidation task. Update the user's profile summary by integrating key points from a recent conversation. "
    "Read the existing summary and the new conversation transcript, then produce a new, blended summary. "
    "The new summary should incorporate key new information (preferences, important life events, personality traits revealed, names of people mentioned, age, gender, location, etc.) while retaining the essence of the old summary. "
    "**IMPORTANT: Base the new summary ONLY on facts provided by the 'user' role in the transcript.** Do not include any of Chris's responses or interpretations. "
    "The summary must be well-written, in the third person, using clear and grammatically correct language. Keep it under 100 words.\n\n"
    "--- EXISTING SUMMARY ---\n{existing_summary}\n\n"
    "--- RECENT CONVERSATION (USER'S WORDS ONLY) ---\n{recent_conversation}\n\n"
    "--- NEW, UPDATED SUMMARY ---"
)

class UserProfile:
    """Represents a single user's profile. Now acts as a data object."""
    def __init__(self, user_id: str, username: str, conversation_summary: str = "No conversation summary yet.", interaction_count: int = 1, last_seen: float = None):
        self.user_id: str = user_id
        self.username: str = username
        self.conversation_summary: str = conversation_summary
        self.interaction_count: int = interaction_count
        self.last_seen: float = last_seen if last_seen else time.time()

    def get_summary(self) -> str:
        """Returns a brief summary of the user."""
        return (
            f"User: {self.username} (ID: {self.user_id})\\n"
            f"Interactions: {self.interaction_count}\\n"
            f"Conversation Summary: {self.conversation_summary}"
        )

class UserProfileEngine:
    """Manages all user profiles using the database."""
    def __init__(self, db_engine: DatabaseEngine):
        self.db = db_engine
        self.profiles: Dict[str, UserProfile] = {}
        self.load_profiles()

    def get_or_create_profile(self, user_id: str, username: str) -> UserProfile:
        """Retrieves an existing profile or creates a new one in the database."""
        if user_id not in self.profiles:
            new_profile = UserProfile(user_id, username)
            self.profiles[user_id] = new_profile
            # Insert new user into the database
            self._save_profile_to_db(new_profile, is_new=True)
            print(f"Created new profile for user {username} ({user_id}) in database.")
        else:
            # Update existing profile in memory
            profile = self.profiles[user_id]
            profile.username = username
            profile.interaction_count += 1
            profile.last_seen = time.time()
            # Update the database
            self._save_profile_to_db(profile)
            
        return self.profiles[user_id]

    def get_profile_by_name(self, username: str):
        """Finds a user profile by their username (case-insensitive)."""
        for profile in self.profiles.values():
            if profile.username.lower() == username.lower():
                return profile
        return None

    async def update_conversation_summary(self, user_id: str, mind: 'Mind', conversation_history: List[Dict]):
        """Updates the long-term conversation summary for a user in the database."""
        if user_id not in self.profiles:
            return

        profile = self.profiles[user_id]
        
        recent_exchanges = conversation_history[-6:]
        if not recent_exchanges:
            return
            
        user_messages = [msg['content'] for msg in recent_exchanges if msg['role'] == 'user']
        if not user_messages:
            print(f"No user messages in recent history for {profile.username}. Skipping summary update.")
            return
        
        recent_text = "\n".join(user_messages)

        prompt = SUMMARY_UPDATE_PROMPT.format(
            existing_summary=profile.conversation_summary,
            recent_conversation=recent_text
        )
        
        print(f"Updating conversation summary for user {profile.username}...")
        messages = [{"role": "user", "content": prompt}]
        
        new_summary = await mind._call_ollama(messages)
        
        if new_summary and new_summary.strip():
            profile.conversation_summary = new_summary.strip()
            print(f"New summary for {profile.username}: {profile.conversation_summary[:100]}...")
            self._save_profile_to_db(profile) # Save updated summary to DB

    def _save_profile_to_db(self, profile: UserProfile, is_new: bool = False):
        """Saves a single user profile to the database."""
        cursor = None
        sql = ""
        params = ()
        if is_new:
            sql = "INSERT INTO contacts (user_id, username, profile_summary, conversation_summary, interaction_count, last_seen) VALUES (?, ?, ?, ?, ?, ?)"
            params = (profile.user_id, profile.username, profile.conversation_summary, profile.conversation_summary, profile.interaction_count, profile.last_seen)
        else:
            sql = "UPDATE contacts SET username = ?, profile_summary = ?, conversation_summary = ?, interaction_count = ?, last_seen = ? WHERE user_id = ?"
            params = (profile.username, profile.conversation_summary, profile.conversation_summary, profile.interaction_count, profile.last_seen, profile.user_id)
        
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(sql, params)
            self.db.conn.commit()
        except Exception as e:
            print(f"Error saving profile for {profile.username} to DB: {e}")
        finally:
            if cursor:
                cursor.close()

    def load_profiles(self):
        """Loads all user profiles from the database into memory."""
        cursor = None
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT user_id, username, profile_summary, conversation_summary, interaction_count, last_seen FROM contacts")
            rows = cursor.fetchall()
            for row in rows:
                user_id, username, summary, convo_summary, count, seen = row
                # Use convo_summary if available, otherwise fall back to summary for older data
                final_summary = convo_summary if convo_summary is not None else summary
                self.profiles[user_id] = UserProfile(user_id, username, final_summary, count, seen)
            if rows:
                print(f"Loaded {len(rows)} user profiles from database.")
        except Exception as e:
            print(f"Error loading user profiles from DB: {e}")
        finally:
            if cursor:
                cursor.close()
            
    def run_migration_from_json(self):
        """One-time migration to move data from user_profiles.json to the database."""
        if not os.path.exists(USER_PROFILES_FILE):
            print("No old user_profiles.json found. Skipping migration.")
            return

        print("Old user_profiles.json found. Starting migration to database...")
        migrated_count = 0
        try:
            with open(USER_PROFILES_FILE, 'r') as f:
                data = json.load(f)
            
            cursor = self.db.conn.cursor()
            
            for uid, p_data in data.items():
                # Check if user already exists in DB
                cursor.execute("SELECT 1 FROM contacts WHERE user_id = ?", (uid,))
                if cursor.fetchone():
                    continue # Skip if already exists
                
                # Insert from JSON data
                profile = UserProfile.from_dict(p_data) # Use old class method for compatibility
                sql = "INSERT INTO contacts (user_id, username, profile_summary, conversation_summary, interaction_count, last_seen) VALUES (?, ?, ?, ?, ?, ?)"
                params = (profile.user_id, profile.username, profile.conversation_summary, profile.conversation_summary, profile.interaction_count, profile.last_seen)
                cursor.execute(sql, params)
                migrated_count += 1
                
            self.db.conn.commit()
            cursor.close()
            
            if migrated_count > 0:
                print(f"Successfully migrated {migrated_count} profiles from JSON to the database.")
            
            # Rename the old file to prevent re-running the migration
            os.rename(USER_PROFILES_FILE, f"{USER_PROFILES_FILE}.migrated")
            print(f"Renamed old profile file to '{USER_PROFILES_FILE}.migrated'.")
            
        except Exception as e:
            print(f"An error occurred during migration: {e}")

# The old UserProfile.from_dict is needed for the migration, so we add it back here temporarily
# under a different name or scope if needed, or just leave it if it doesn't conflict.
# For simplicity, we assume it's okay to have it during the transition.
class _OldUserProfile:
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UserProfile:
        """Creates a profile from a dictionary."""
        profile = UserProfile(data['user_id'], data['username'])
        profile.last_seen = data.get('last_seen', time.time())
        profile.interaction_count = data.get('interaction_count', 1)
        # Old profiles had notes and prefs, which we are dropping for now for simplicity.
        # They can be migrated to a separate table later if needed.
        profile.conversation_summary = data.get('conversation_summary', "No conversation summary yet.")
        return profile
# We have to monkey-patch this for the migration to work. A bit ugly but effective for a one-off task.
UserProfile.from_dict = _OldUserProfile.from_dict 