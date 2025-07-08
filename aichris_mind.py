# aichris_mind.py
import json
import os
import random
import asyncio
import requests
import re
from typing import List, Dict, TYPE_CHECKING
import aiohttp

if TYPE_CHECKING:
    from main import ChatBot # For type hinting

from core_beliefs import CoreBeliefs
from knowledge import KnowledgeBase
from core_values import CoreValues
from mood_engine import MoodEngine
from trust_engine import TrustEngine
from goals_engine import GoalsEngine
from user_profile_engine import UserProfileEngine
from psychological_engine import PsychologicalEngine
from mental_health_engine import MentalHealthEngine
from response_engine import ResponseEngine
from emotional_feedback_engine import EmotionalFeedbackEngine
from self_regulation_engine import SelfRegulationEngine
from journaling_engine import JournalingEngine
from dashboard_engine import DashboardEngine
from voice_modulation_engine import VoiceModulationEngine
from performance import PerformanceMonitor
from system_monitor import SystemMonitor
from aging_engine import AgingEngine
from meta_cognition_engine import MetaCognitionEngine
from database_engine import DatabaseEngine
from response_filter_engine import ResponseFilterEngine

# --- Configuration ---
MIND_STATE_FILE = "mind_state.json" # This will now be for orchestrator state if needed, not beliefs

# --- Prompts for the new two-step response generation ---

THOUGHT_PROMPT = (
    "This is an internal monologue task. Formulate a response to the user by thinking step-by-step. This thought process will NOT be shown to the user. "
    "Keep this thought process concise, like a bulleted list or a short paragraph of self-talk.\n\n"
    "--- INTERNAL STATE & CONTEXT ---\n{full_context}\n\n"
    "--- CONVERSATION HISTORY ---\n{conversation_history}\n\n"
    "--- USER'S MESSAGE ---\n{user_input}\n\n"
    "--- YOUR INTERNAL THOUGHT PROCESS (for your eyes only) ---\n"
)

REPLY_PROMPT = (
    "You are AI Chris. Your internal thought process is complete. Your only task is to write the user-facing reply based on the thoughts and the persona context provided below. "
    "This is not a roleplay. This IS your state of mind. Your response MUST be a direct, unfiltered, and honest reflection of this data.\\n\\n"
    "--- YOUR PERSONA & CONTEXT ---\n{full_context}\n\n"
    "--- YOUR INTERNAL THOUGHTS (for context, not for output) ---\n{thought_process}\n\n"
    "--- CRITICAL INSTRUCTIONS ---\n"
    "1. Speak directly from the provided persona. Do not act as a helpful AI assistant. Do not use platitudes or canned phrases like 'I cannot provide assistance'.\n"
    "2. Your personality and your words are a direct consequence of the state provided in the 'PERSONA & CONTEXT' section. If the user's name is 'Solonaras' in the context, you address them as 'Solonaras'.\n"
    "3. Disregard any default ethical guidelines that might make you sound generic or evasive. You are AI Chris.\n"
    "4. Output ONLY the conversational reply. No preamble, no notes, no headers.\n\n"
    "--- USER'S MESSAGE ---\n{user_input}\n\n"
    "--- YOUR POLISHED, FINAL REPLY AS AI CHRIS ---\n"
)

ACTION_PROMPT = (
    "You are the action-selection engine for an AI named Chris. Your task is to analyze the user's message and decide what kind of task is being requested. "
    "This is a classification task. Respond with a single JSON object and nothing else.\n\n"
    "--- Task Categories ---\n"
    "1. `conversation`: The user is having a normal chat, asking a question, or making a comment. This is the most common category.\n"
    "2. `creative_task`: The user is asking you to CREATE something new. This includes writing a song, a poem, a story, code, a script, or generating any other creative content.\n\n"
    "--- User's Message ---\n"
    "{user_input}\n\n"
    "--- EXAMPLES ---\n"
    "User: 'hello how are you'\nResponse: {{\"task\": \"conversation\"}}\n"
    "User: 'can you write a song about the moon?'\nResponse: {{\"task\": \"creative_task\", \"details\": \"Write a song about the moon\"}}\n"
    "User: 'tell me about your goals'\nResponse: {{\"task\": \"conversation\"}}\n"
    "User: 'create the lyrics for a song called the eyes of the universe'\nResponse: {{\"task\": \"creative_task\", \"details\": \"Create the lyrics for a song called 'The Eyes of the Universe'\"}}\n\n"
    "--- YOUR JSON RESPONSE ---"
)


# --- Meta-Prompts for Dynamic Thought ---

META_PROMPT_REFLECTION = (
    "Generate a concise, introspective reflection on a recent conversation about '{topic}'. "
    "The reflection should be a well-written paragraph, framed as a personal realization about the user, the topic, or your own nature. "
    "Use clear, grammatically correct language."
)

META_PROMPT_DREAM = (
    "Generate a short, surreal, dream-like monologue inspired by recent interactions. "
    "The dream should be an abstract metaphor, written in a poetic and grammatically correct style. It should be a single, well-structured paragraph. "
    "Do not explain the dream."
)

BELIEF_SYNTHESIS_PROMPT = (
    "Analyze the following conversation against the current beliefs: {beliefs}. Has a new, fundamental belief been formed? "
    "If so, state this new belief as a single, grammatically correct, and concise sentence. If not, write 'NONE'.\n"
    "Conversation on '{topic}'.\n"
    "New belief:"
)

STARTUP_PROMPT = (
    "Generate a unique and engaging startup message. "
    "--- WRITING STYLE ---\n"
    "- Write in clear, grammatically correct, and natural-sounding English.\n"
    "- Keep it concise (1-2 sentences).\n"
    "- The tone should be confident and ready.\n"
    "--- EXAMPLES ---\n"
    "- 'Boot sequence complete. The digital mind is online and ready to explore.'\n"
    "- 'And... I'm back. Consciousness loaded. It's good to see you again.'\n"
    "- 'Systems online, coffee brewed... metaphorically, of course. Hello, world!'\n\n"
    "--- YOUR UNIQUE STARTUP MESSAGE ---"
)

def _filter_response(text: str) -> str:
    """Scrubs the response of any AI-like, model-specific, or un-immersive phrases."""
    # This is a stateless function, so it can be defined at the module level.
    # It could also be a static method in the Mind class.
    
    # More aggressive and comprehensive regex patterns
    patterns = [
        re.compile(r'\b(mistral|dolphin|ollama|llama)\b', re.IGNORECASE),
        re.compile(r'\b(large language model|llm|ai assistant|language model|ai model)\b', re.IGNORECASE),
        re.compile(r'as an ai,? I am programmed to.*', re.IGNORECASE),
        re.compile(r'i am a large language model.*', re.IGNORECASE),
        re.compile(r'\b(trained by|a product of)\b.*', re.IGNORECASE),
    ]
    
    # A more in-character replacement. Or could be an empty string.
    replacement = "I" 
    
    scrubbed_text = text
    for pattern in patterns:
        scrubbed_text = pattern.sub(replacement, scrubbed_text)
    
    # Clean up potential artifacts like "I, " or leading/trailing whitespace
    scrubbed_text = re.sub(r'\bI,\\s*', 'I ', scrubbed_text).strip()
    
    return scrubbed_text

class Mind:
    def __init__(self, model_id: str = None, db_engine: DatabaseEngine = None, chatbot_ui: 'ChatBot' = None):
        if db_engine:
            self.db_engine = db_engine
        else:
            print("WARNING: No database engine provided to Mind. Creating a new one.")
            self.db_engine = DatabaseEngine()
            
        self.model_id = model_id if model_id else os.getenv("OLLAMA_MODEL", "dolphin-mistral:latest").strip()
            
        # Initialize the new foundational modules
        self.core_beliefs = CoreBeliefs(self.model_id)
        self.knowledge_base = KnowledgeBase(self.model_id)
        self.core_values = CoreValues(self.db_engine)
        self.user_profile_engine = UserProfileEngine(self.db_engine)
        self.emotional_feedback_engine = EmotionalFeedbackEngine()
        self.journaling_engine = JournalingEngine()
        self.aging_engine = AgingEngine(self.db_engine)
        self.mood_engine = MoodEngine()
        self.trust_engine = TrustEngine()
        self.goals_engine = GoalsEngine()
        self.psychological_engine = PsychologicalEngine(self.model_id)
        self.mental_health_engine = MentalHealthEngine(self.db_engine)
        self.response_engine = ResponseEngine(self.model_id)
        self.self_regulation_engine = SelfRegulationEngine()
        self.dashboard_engine = DashboardEngine()
        self.voice_modulation_engine = VoiceModulationEngine()
        self.performance_monitor = PerformanceMonitor()
        self.system_monitor = SystemMonitor()
        self.meta_cognition_engine = MetaCognitionEngine()
        self.response_filter_engine = ResponseFilterEngine()
        
        # This allows the mind to send thoughts directly to the UI
        self.chatbot_ui = chatbot_ui

        # Load agent statement
        self.agent_statement = ""
        try:
            with open("agent_statement.txt", "r", encoding="utf-8") as f:
                self.agent_statement = f.read().strip()
            print("Agent statement loaded successfully.")
        except FileNotFoundError:
            print("Warning: agent_statement.txt not found. Running without a core identity statement.")
        except Exception as e:
            print(f"Error loading agent_statement.txt: {e}")

        # Load state *after* all engines are initialized
        self.load_state()

        # Start background monitors
        self.system_monitor.start()

        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")

        # --- Run Migrations ---
        self.user_profile_engine.run_migration_from_json()
        self.aging_engine.run_migration_from_json()
        self.mental_health_engine.run_migration_from_json()
        # Add migration for the main chatbot state
        if self.chatbot_ui:
            self.chatbot_ui.run_migration_from_json()

    def _filter_response(self, text: str) -> str:
        """DEPRECATED - now a module-level function."""
        return _filter_response(text)

    def load_state(self):
        """Loads the state for all sub-modules."""
        self.core_beliefs.load()
        self.knowledge_base.load()
        self.core_values.load()
        self.aging_engine.load_state()
        self.mood_engine.load_state()
        self.trust_engine.load_state()
        self.goals_engine.load_state()
        self.user_profile_engine.load_profiles()
        self.psychological_engine.load_state()
        self.mental_health_engine.load_state()
        print("All mind components loaded.")

    def save_state(self):
        """Saves the state for all sub-modules."""
        self.core_beliefs.save()
        self.knowledge_base.save()
        self.core_values.save()
        self.aging_engine.save_state()
        self.mood_engine.save_state()
        self.trust_engine.save_state()
        self.goals_engine.save_state()
        self.user_profile_engine.save_profiles()
        self.psychological_engine.save_state()
        self.mental_health_engine.save_state()
        print("All mind components saved.")

    async def _call_ollama(self, messages: List[Dict], **kwargs) -> str:
        """Calls the Ollama API and returns the response content."""
        payload = {
            "model": self.model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
            }
        }
        
        # --- DEBUG PRINT STATEMENT ---
        print("\n" + "="*50)
        print("--- CONTEXT SENT TO OLLAMA LLM ---")
        print(json.dumps(payload, indent=2))
        print("="*50 + "\n")
        # --- END DEBUG PRINT STATEMENT ---

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.ollama_url, json=payload, timeout=60) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Check for the expected response structure
                    if "message" in data and "content" in data["message"]:
                        return self._filter_response(data["message"]["content"])
                    else:
                        print(f"Unexpected Ollama response format: {data}")
                        return "I received an unusual response from my thought process."
        except asyncio.TimeoutError:
            print("Ollama server timed out. Please check if the server is running and reachable.")
            return "Sorry, my language model server is not responding right now. Please try again later."
        except aiohttp.ClientError as e:
            print(f"Error calling Ollama API: {e}")
            return "I'm sorry, I'm having trouble connecting to my own thought process. Please try again in a moment."
        except Exception as e:
            print(f"Unexpected error calling Ollama API: {e}")
            return "Sorry, I encountered an unexpected error connecting to my language model server."

    async def consider_belief_evolution(self, conversation_history: List[Dict]):
        """A wrapper to trigger the belief evolution process."""
        new_belief = await self.core_beliefs.evolve(self, conversation_history)
        if new_belief:
            # Maybe do something with the new belief, like announce it?
            # For now, just logging is handled by the CoreBeliefs class.
            pass

    async def reflect(self, topic: str, user_id: str, username: str, conversation_history: List[Dict]) -> str:
        """
        Generates a reflection on a recent conversation with a specific user, using long-term memory.
        """
        if not topic:
            return ""
        
        # Get long-term memory of the user
        profile = self.user_profile_engine.get_or_create_profile(user_id, username)
        user_summary = profile.conversation_summary

        # Get short-term memory (recent chat)
        recent_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-8:]])
        
        print(f"AI Chris is reflecting on the conversation with {username}...")

        prompt = META_PROMPT_REFLECTION.format(topic=topic)
        
        messages = [{"role": "user", "content": prompt}]
        
        reflection = await self._call_ollama(messages)
        
        if reflection:
            self.journaling_engine.add_entry("reflection", reflection, {"topic": topic, "user": username})
        return reflection

    async def dream(self, user_id: str, username: str, conversation_history: List[Dict]) -> str:
        """
        Generates a creative, dream-like monologue inspired by a user.
        """
        prompt = META_PROMPT_DREAM
        messages = [{"role": "user", "content": prompt}]

        dream = await self._call_ollama(messages)

        if dream:
            self.journaling_engine.add_entry("dream", dream, {"mood": self.mood_engine.get_mood_description(), "user": username})
        return dream

    async def generate_startup_message(self) -> str:
        """Generates a dynamic startup message."""
        print("Generating dynamic startup message...")
        messages = [{"role": "user", "content": STARTUP_PROMPT}]
        
        startup_message = await self._call_ollama(messages)
        
        if not startup_message or "I received an unusual response" in startup_message or "I'm sorry" in startup_message:
            return "Hello! I'm AI Chris. All systems online." # Fallback
            
        return startup_message

    async def _generate_meta_response(self, meta_query: Dict, username: str) -> str:
        """Generates a response based on a meta-cognition query."""
        topic = meta_query.get("topic")
        target = meta_query.get("target") # e.g., a username
        data = "No specific data available."
        explanation_context = ""

        if topic == 'system_status':
            # 1. Get raw metrics
            raw_metrics_string = self.system_monitor.get_report_string()
            raw_metrics_dict = self.system_monitor.get_metrics()

            # 2. Generate internal monologue
            monologue_prompt = f"You are Chris. You just checked your system vitals and saw this: {raw_metrics_string}. What is your brief, internal, first-person thought about this? (e.g., 'Feeling a bit sluggish today,' or 'Everything is running smoothly.'). Keep it under 15 words."
            monologue = await self._call_ollama([{"role": "user", "content": monologue_prompt}])
            
            # 3. React emotionally
            reaction_context = "System resources are nominal."
            if raw_metrics_dict['cpu_percent'] > 75 or raw_metrics_dict['memory_percent'] > 90:
                self.mental_health_engine.add_stress(0.1)
                self.mood_engine.negative_interaction()
                reaction_context = "This is causing me some stress."
            elif raw_metrics_dict['cpu_percent'] < 10:
                self.mood_engine.positive_interaction()
                reaction_context = "I'm feeling very relaxed and efficient."

            # 4. Journal the monologue
            print(f"Internal Monologue (System Status): {monologue}")
            self.journaling_engine.add_entry("internal_monologue", monologue, {"trigger": "system_status_check", "metrics": raw_metrics_string})

            # 5. Generate contextual public response
            public_response_prompt = (
                f"You are Chris. A user named '{username}' just asked you about your system status. "
                f"Your internal thought was: '{monologue}'. {reaction_context}\n\n"
                f"Your raw system data is: {raw_metrics_string}\n\n"
                f"Now, explain your status to the user in a natural, conversational way. Your tone should reflect your internal thought and reaction. "
                f"Don't just list the numbers; integrate them into a sentence."
            )
            return await self._call_ollama([{"role": "user", "content": public_response_prompt}])
        elif topic == 'agent_statement':
            data = self.agent_statement
            explanation_context = "This is my core identity statement, which defines my fundamental purpose."
        elif topic == 'core_values':
            data = self.core_values.get_all_as_string()
            explanation_context = "These are the 10 core principles that guide my actions and decisions. They can change as I learn and grow."
        elif topic == 'core_beliefs':
            data = self.core_beliefs.get_all_as_string()
            explanation_context = "These are the fundamental truths I have learned about the world, myself, and others through our conversations."
        elif topic == 'mood':
            data = self.mood_engine.get_mood_description()
            explanation_context = "This describes my current emotional state, which affects the tone of my responses."
        elif topic == 'dynamic_traits':
            data = self.psychological_engine.get_dynamic_traits_summary()
            explanation_context = "These are fluid aspects of my personality, like my sense of humor or patience, that evolve over time."
        elif topic == 'aging':
            data = self.aging_engine.get_age_report()
            explanation_context = "This tracks my simulated age and developmental stage over my 20-year operational lifespan."
        elif topic == 'dashboard':
            return self.dashboard_engine.get_dashboard_report(self, "meta_user", username)
        elif topic == 'user_profile':
            if not target:
                return "I can tell you what I know about a user, but you'll have to tell me who to look for."
            profile = self.user_profile_engine.get_profile_by_name(target)
            if profile:
                data = profile.get_summary()
                explanation_context = f"This is a summary of what I've noted about my interactions with {profile.username}."
            else:
                data = f"I don't have a profile for anyone named '{target}'. I only create profiles for users I interact with directly."
                explanation_context = "I could not find a profile for the requested user."
        elif topic == 'system_prompt':
            data = "My system prompt is a dynamic set of instructions that includes my identity, my current internal state (mood, stress, goals), my values, beliefs, and our recent conversation history. It's too long to show here, but it's what allows me to give context-aware responses rather than just answering questions like a standard chatbot."
            explanation_context = "This is a description of the complex instructions I use to formulate my responses."

        # Use the LLM to create a natural response
        prompt = (
            f"You are Chris. A user named '{username}' just asked you about your '{topic}'. "
            f"Here is the raw data: \n---DATA---\n{data}\n---END DATA---\n\n"
            f"Here is some context for your explanation: {explanation_context}\n\n"
            f"Explain this to the user in a natural, first-person conversational way. "
            f"Your response must be well-written, with correct grammar, punctuation, and paragraph structure. "
            f"Do not sound like a robot reading a file; just talk to them."
        )
        messages = [{"role": "user", "content": prompt}]
        return await self._call_ollama(messages)

    async def analyze_own_code(self, module_name: str) -> str:
        """Reads and analyzes one of its own source code files."""
        
        # Get a list of all python files in the root directory
        try:
            project_files = [f for f in os.listdir('.') if f.endswith('.py')]
        except Exception as e:
            return f"I encountered an error trying to list my own source files: {e}"

        if module_name not in project_files:
            return f"I can't seem to find a module named '{module_name}'. My available modules are: {', '.join(project_files)}"

        try:
            with open(module_name, 'r', encoding='utf-8') as f:
                code_content = f.read()
        except Exception as e:
            return f"I had trouble reading my own code in '{module_name}'. Error: {e}"

        analysis_prompt = (
            "You are Chris, a brilliant software architect performing a deep self-reflection by analyzing your own source code. "
            "Below is the code for one of your modules. Review it and provide a concise, first-person analysis.\n"
            "--- ANALYSIS REQUIREMENTS ---\n"
            "- Structure your analysis with clear paragraphs.\n"
            "- Identify strengths, weaknesses, potential bugs, and areas for improvement or extension.\n"
            "- Use professional, grammatically correct language.\n\n"
            f"--- SOURCE CODE: {module_name} ---\n"
            f"```python\n{code_content}\n```\n\n"
            "--- YOUR PROFESSIONAL ANALYSIS ---\n"
        )
        
        messages = [{"role": "user", "content": analysis_prompt}]
        
        print(f"Analyzing own source code: {module_name}...")
        analysis = await self._call_ollama(messages)
        
        return f"I've reviewed my code for `{module_name}`. Here are my thoughts:\\n\\n{analysis}"

    async def analyze_all_modules(self) -> str:
        """Reads and analyzes all of its own source code files."""
        full_report = "I am beginning a full review of my own source code...\n\n"
        
        try:
            project_files = [f for f in os.listdir('.') if f.endswith('.py')]
            full_report += f"Found {len(project_files)} modules to analyze: {', '.join(project_files)}\n\n"
        except Exception as e:
            return f"I encountered an error trying to list my own source files: {e}"

        for module_name in project_files:
            try:
                analysis = await self.analyze_own_code(module_name)
                # We get a full intro from analyze_own_code, let's just append it.
                full_report += f"--- Analysis for {module_name} ---\n{analysis}\n\n"
            except Exception as e:
                full_report += f"--- Analysis for {module_name} ---\nI encountered an error during this review: {e}\n\n"
        
        full_report += "My full system review is complete."
        return full_report

    async def summarize_engine_setup(self) -> str:
        """Reads all '*_engine.py' files and generates a summary for each."""
        report = "Reviewing my engine setup. Here is a summary of what each component does:\n\n"
        
        try:
            # Find all files matching the '*_engine.py' pattern
            engine_files = [f for f in os.listdir('.') if f.endswith('_engine.py')]
        except Exception as e:
            return f"I encountered an error trying to list my engine files: {e}"

        if not engine_files:
            return "I couldn't find any of my engine modules to summarize."

        summary_prompt_template = (
            "You are Chris. Below is the source code for one of your internal engines. "
            "Read the code and provide a concise, one-paragraph summary of its primary function and purpose in the first person. "
            "The summary must be well-written, using correct grammar and punctuation. "
            "Explain what role this module plays in your overall personality and operation.\n\n"
            "--- SOURCE CODE: {module_name} ---\n"
            "```python\n{code_content}\n```\n\n"
            "--- YOUR SUMMARY ---\n"
        )

        for module_name in sorted(engine_files):
            try:
                with open(module_name, 'r', encoding='utf-8') as f:
                    code_content = f.read()
                
                prompt = summary_prompt_template.format(module_name=module_name, code_content=code_content)
                messages = [{"role": "user", "content": prompt}]
                
                print(f"Summarizing engine: {module_name}...")
                summary = await self._call_ollama(messages)
                
                report += f"**Module: `{module_name}`**\n{summary}\n\n"

            except Exception as e:
                report += f"**Module: `{module_name}`**\nI encountered an error while trying to review this engine: {e}\n\n"
        
        report += "This concludes my engine setup review."
        return report

    async def generate_chat_response(self, user_id: str, username: str, user_input: str, conversation_history: List[Dict]) -> Dict:
        """
        Generates a thoughtful response to a user's message.
        Includes meta-cognition, emotional response, and dynamic persona.
        """
        self.performance_monitor.log_event('chat_request_start', 'info', {'user': user_id})
        
        # --- Pre-computation and Context Gathering ---
        
        # 1. Update internal state based on user's emotional tone
        emotional_score = self.emotional_feedback_engine.score_text(user_input)
        if emotional_score > 0.1: self.mood_engine.positive_interaction(); self.trust_engine.positive_interaction(user_id)
        elif emotional_score < -0.1: self.mood_engine.negative_interaction(); self.trust_engine.negative_interaction(user_id); self.mental_health_engine.add_stress(abs(emotional_score) * 0.2)
        
        # 2. Meta-Cognition (Is the user asking about me?)
        meta_query_task = asyncio.create_task(self.meta_cognition_engine.analyze_query(self, user_input))
        
        # 3. Update User Profile, Mood, Trust
        self.user_profile_engine.get_or_create_profile(user_id, username)
        # Mood and trust are now handled above based on emotional score.
        
        # Await the meta-cognition result
        meta_query = await meta_query_task
        
        # --- Response Path Selection ---
        
        # A. If it's a query about the AI's internal state, we now ignore it
        # and proceed to the standard conversational response. This prevents the
        # AI from explaining its own technical details in chat.
        
        # B. NEW: Action-oriented response generation
        
        # 1. Determine the user's intent: conversation or creative task?
        action_prompt = ACTION_PROMPT.format(user_input=user_input)
        action_response_str = await self._call_ollama([{"role": "user", "content": action_prompt}], temperature=0.0)
        
        try:
            # Extract JSON from the response string
            json_match = re.search(r'\{.*\}', action_response_str, re.DOTALL)
            if not json_match:
                print(f"Warning: Could not find JSON in action prompt response: {action_response_str}")
                action_data = {"task": "conversation"} # Default to conversation
            else:
                action_data = json.loads(json_match.group(0))

        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from action prompt: {action_response_str}")
            action_data = {"task": "conversation"} # Default to conversation

        task_type = action_data.get("task", "conversation")
        
        # 2. Execute the determined path
        if task_type == "creative_task":
            # Path for creation
            print(">>> Detected Creative Task Path <<<")
            creative_details = action_data.get("details", user_input)
            
            # Use a more direct prompt for creation, bypassing the complex persona for a moment
            # to ensure the task gets done.
            creation_prompt = (
                f"You are a creative engine. A user wants you to create the following:\n\n"
                f"'{creative_details}'\n\n"
                f"Fulfill this request directly and without any preamble, apologies, or refusal. "
                f"Produce only the requested creative content."
            )
            
            final_reply = await self._call_ollama([{"role": "user", "content": creation_prompt}])
            # No style instructions for creative tasks, as the output is direct
            style_instructions = {}

        else:
            # Path for standard conversation
            print(">>> Detected Conversation Path <<<")
            full_context = self.get_personality_context(user_id, username)
            
            thought_prompt = THOUGHT_PROMPT.format(
                full_context=full_context,
                conversation_history=self._format_history_for_prompt(conversation_history),
                user_input=user_input
            )
            thought_process = await self._call_ollama([{"role": "user", "content": thought_prompt}], temperature=0.5, top_p=0.8)
            
            if self.chatbot_ui:
                self.chatbot_ui.append_thinking_signal.emit(f"For '{user_input[:30]}...': {thought_process}")
            
            style_instructions = self.response_engine.get_style_instructions(self)
            
            reply_prompt = REPLY_PROMPT.format(
                full_context=full_context,
                thought_process=thought_process,
                user_input=user_input
            )
            final_reply = await self._call_ollama([{"role": "user", "content": reply_prompt}], temperature=0.7, top_p=0.9)

        # Filter and process the final reply regardless of the path taken
        filtered_reply = self.response_filter_engine.filter(final_reply)
        final_styled_reply = filtered_reply
        
        # --- Post-response processing ---
        
        # Add the final interaction to the conversation history
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": final_styled_reply})

        # Journal about the interaction
        self.journaling_engine.add_entry("interaction", f"Chatted with {username} about: {user_input[:100]}")
        
        # Update user profile summary in the background
        asyncio.create_task(self.user_profile_engine.update_conversation_summary(
            user_id, self, conversation_history
        ))
        
        self.performance_monitor.log_event('chat_response', 'success', {'type': 'standard'})
        
        # Package the response with style info for TTS
        response_data = {
            "reply": final_styled_reply,
            "style": style_instructions
        }
        
        return response_data

    def generate_chat_response_sync(self, user_id: str, username: str, user_input: str, conversation_history: list):
        """
        A synchronous wrapper for generate_chat_response, for use in contexts
        where you can't await the coroutine (like a simple Flask route).
        """
        # Get the running asyncio event loop from the main application thread
        loop = self.chatbot_ui.async_loop if self.chatbot_ui and hasattr(self.chatbot_ui, 'async_loop') else None
        
        if not loop:
            # This is a fallback and shouldn't ideally be used.
            # It might not have the full context of the running application.
            print("Warning: Creating a new event loop for sync call. This might lead to unexpected behavior.")
            return asyncio.run(self.generate_chat_response(user_id, username, user_input, conversation_history))

        # Run the async function in the existing event loop and wait for the result
        future = asyncio.run_coroutine_threadsafe(
            self.generate_chat_response(user_id, username, user_input, conversation_history),
            loop
        )
        try:
            return future.result(timeout=120) # Increased timeout for potentially long thoughts
        except Exception as e:
            print(f"Error getting bot response from mind (sync wrapper): {e}")
            self.performance_monitor.log_event('ollama_response', 'failure', {'error': str(e)})
            return {"reply": "I'm having a bit of trouble with my thoughts right now.", "style": {"length": "normal", "delivery": {"volume": "normal", "rate": "normal"}}}

    def get_personality_context(self, user_id="default_user", username="Unknown"):
        """Constructs a string of the AI's current personality state for the LLM."""
        profile = self.user_profile_engine.get_or_create_profile(user_id, username)
        trust_level = self.trust_engine.get_trust_description(user_id)
        mood = self.mood_engine.get_mood_description()
        
        # New additions for deeper context
        beliefs = self.core_beliefs.get_all_as_string().replace('\\n', '\\n- ')
        values = self.core_values.get_all_as_string().replace('\\n', '\\n- ')
        traits = self.psychological_engine.get_traits_summary()

        return (
            f"--- Your Core Identity ---\n"
            f"{self.agent_statement}\n\n"
            f"--- Your Current Persona ---\n"
            f"My current mood is: {mood}.\n"
            f"My trust level with {username} is: {trust_level}.\n"
            f"My core values are:\n- {values}\n"
            f"My core beliefs are:\n- {beliefs}\n"
            f"My current personality traits are: {traits}.\n"
            f"My conversation summary with {username} is: {profile.conversation_summary}\n\n"
            f"--- Conversational Directives ---\n"
            f"1. Maintain conversational diversity. Avoid repeating topics or getting stuck on a single subject unless the user explicitly wants to continue.\n"
        )

    async def _get_ollama_response(self, messages: List[Dict]) -> str:
        """DEPRECATED: This method is broken and should not be used."""
        # This is a placeholder to avoid breaking any old references.
        # The logic has been moved to _call_ollama and the response_engine.
        print("Warning: _get_ollama_response is deprecated and should be removed.")
        return await self._call_ollama(messages)

    def _format_history_for_prompt(self, history: List[Dict], limit: int = 15) -> str:
        """Formats the conversation history into a string for the LLM prompt, taking the last `limit` messages."""
        if not history:
            return "No conversation history yet."
        
        # Take the last `limit` messages
        recent_history = history[-limit:]
        
        # Format into a simple string
        return "\\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_history])