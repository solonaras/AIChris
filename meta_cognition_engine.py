import asyncio
from typing import List, Dict, Optional
import json
import re

META_QUERY_PROMPT = (
    "This is an intent detection task. Analyze the user's message to a digital person named Chris and determine if the user is asking a direct question about one of Chris's specific internal systems or about a specific user profile he might have stored.\\n\\n"
    "--- System Components & Keywords ---\\n"
    "- Hardware performance (CPU, memory, uptime): 'system_status'. Triggered by phrases like 'system status'.\\n"
    "- Guiding principles or morals: 'core_values'. Triggered by 'what are your values', 'your principles'.\\n"
    "- Fundamental learned truths: 'core_beliefs'. Triggered by 'what are your beliefs'.\\n"
    "- Current emotional state: 'mood'. Triggered by 'what is your current mood', 'your mood status'.\\n"
    "- Evolving personality attributes (humor, patience, etc.): 'dynamic_traits'. Triggered by 'your personality', 'your traits'.\\n"
    "- Age or life stage: 'aging'. Triggered by 'how old are you', 'your age'.\\n"
    "- The full internal dashboard: 'dashboard'. Triggered by 'show me your dashboard', 'full report'.\\n"
    "- The underlying instructions or prompt that guides responses: 'system_prompt'. Triggered by 'your instructions', 'system prompt'.\\n"
    "- A specific user's profile: 'user_profile'. Triggered by 'what do you know about [username]', 'my profile'.\\n\\n"
    "--- INSTRUCTIONS ---\\n"
    "1. Analyze the user's message carefully. It must be a direct QUESTION about one of the components.\\n"
    "2. **CRITICAL**: Ignore simple greetings like 'hello', 'hi', 'hey there', or 'how are you'. These are NOT queries about the system status. For these, you MUST return {{\"topic\": \"NONE\"}}.\\n"
    "3. **IMPORTANT**: Ignore any user message that is a command, such as those starting with '/' or '!'. For example, if the user says '/review main.py', this is a command, not a query. In this case, you MUST return {{\"topic\": \"NONE\"}}.\\n"
    "4. If the message is a valid query about a system component, return a JSON object: {{\"topic\": \"keyword\"}}.\\n"
    "5. If the message is a query about a user (e.g., 'what do you know about solonaras?'), identify the username and return a JSON object: {{\"topic\": \"user_profile\", \"target\": \"username\"}}.\\n"
    "6. If the message is a general chat message, a command, a greeting, or not a direct question about an internal state, return: {{\"topic\": \"NONE\"}}.\\n"
    "7. **DENYLIST**: If the user's message contains phrases like 'answer my question', 'don't read prompts', or 'stop talking about prompts', it is a complaint, NOT a query. You MUST return {{\"topic\": \"NONE\"}}.\\n\\n"
    "--- Analysis ---\\n"
    "User Message: \"{user_input}\"\\n\\n"
    "JSON Response:"
)

class MetaCognitionEngine:
    """Handles self-awareness and ability to talk about internal components."""
    
    async def analyze_query(self, mind, user_input: str) -> Optional[Dict]:
        """
        Analyzes the user's input to see if it's a query about internal state.
        Returns a dictionary with 'topic' and optional 'target', or None.
        """
        prompt = META_QUERY_PROMPT.format(user_input=user_input)
        messages = [{"role": "user", "content": prompt}]
        
        # Manually check the denylist first for a faster, more reliable result.
        denylist = ["answer my question", "don't read prompts", "stop talking"]
        for phrase in denylist:
            if phrase in user_input.lower():
                print("Meta-cognition query blocked by denylist.")
                return None

        # Use the mind's central and filtered API caller
        response_text = await mind._call_ollama(messages)
        
        try:
            # Use regex to find the JSON object within the response text.
            # This is more robust against the model adding conversational text.
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if not json_match:
                print(f"No JSON object found in meta-cognition response: {response_text}")
                return None
            
            response_json = json_match.group(0)
            data = json.loads(response_json)
            topic = data.get("topic", "NONE").lower().strip()

            if topic != 'none' and topic in [
                'system_status', 'agent_statement', 'core_values', 'core_beliefs', 
                'mood', 'dynamic_traits', 'aging', 'dashboard', 'system_prompt', 'user_profile'
            ]:
                print(f"Meta-cognition query detected: {data}")
                return data # Return the whole dictionary
        
        except (json.JSONDecodeError, AttributeError) as e:
             print(f"Could not decode or parse meta-cognition response. Error: {e}, Response: {response_text}")

        return None 