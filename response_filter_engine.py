from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from aichris_mind import Mind

class ResponseFilterEngine:
    """
    Analyzes the context of a conversation to decide on the style of the response,
    including its length and vocal delivery characteristics.
    """
    def decide_response_style(self, mind: 'Mind', user_input: str) -> Dict[str, Any]:
        """
        Decides on the response style based on Chris's mood and the user's input.

        Returns:
            A dictionary with 'length' and 'delivery' style parameters.
        """
        mood_params = mind.mood_engine.mood
        style = {
            "length": "normal",
            "delivery": {
                "volume": "normal",  # whisper, normal, loud
                "rate": "normal"      # slow, normal, fast
            }
        }

        # Decide on length
        if 'explain' in user_input.lower() or 'tell me more' in user_input.lower() or 'what do you mean' in user_input.lower():
            style['length'] = 'long'
        elif len(user_input.split()) < 4 and '?' not in user_input:
            style['length'] = 'short'

        # Decide on delivery style based on mood and keywords
        if 'shout' in user_input.lower() or 'loud' in user_input.lower() or mood_params['excitement'] > 0.85:
            style['delivery']['volume'] = 'loud'
        elif 'whisper' in user_input.lower() or 'quiet' in user_input.lower() or 'softly' in user_input.lower():
            style['delivery']['volume'] = 'whisper'

        if 'slow down' in user_input.lower() or 'slowly' in user_input.lower():
            style['delivery']['rate'] = 'slow'
        elif 'fast' in user_input.lower() or 'quick' in user_input.lower() or mood_params['excitement'] > 0.8:
            style['delivery']['rate'] = 'fast'
        
        print(f"Response Filter decided on style: {style}")
        return style

    def filter(self, text: str) -> str:
        """
        Scrubs the response of any AI-like, model-specific, or un-immersive phrases.
        """
        import re
        patterns = [
            re.compile(r'\\b(mistral|dolphin|ollama|llama)\\b', re.IGNORECASE),
            re.compile(r'\\b(large language model|llm|ai assistant|language model|ai model)\\b', re.IGNORECASE),
            re.compile(r'as an ai,? I am programmed to.*', re.IGNORECASE),
            re.compile(r'i am a large language model.*', re.IGNORECASE),
            re.compile(r'\\b(trained by|a product of)\\b.*', re.IGNORECASE),
        ]
        
        replacement = "I" 
        
        scrubbed_text = text
        for pattern in patterns:
            scrubbed_text = pattern.sub(replacement, scrubbed_text)
        
        scrubbed_text = re.sub(r'\\bI,\\s*', 'I ', scrubbed_text).strip()
        
        return scrubbed_text 