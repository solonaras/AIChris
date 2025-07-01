from typing import Dict

class EmotionalFeedbackEngine:
    """Analyzes user input to determine its emotional content."""

    def __init__(self):
        # Simple keyword-based scoring. More advanced versions could use ML models.
        self.positive_keywords: Dict[str, float] = {
            "love": 0.3, "amazing": 0.3, "thank you": 0.2, "great": 0.2,
            "awesome": 0.3, "cool": 0.1, "perfect": 0.3, "happy": 0.2
        }
        self.negative_keywords: Dict[str, float] = {
            "hate": -0.3, "terrible": -0.3, "stupid": -0.2, "bad": -0.2,
            "wrong": -0.1, "not good": -0.2, "sad": -0.2, "error": -0.1
        }

    def score_text(self, text: str) -> float:
        """
        Scores the emotional valence of a text.
        Returns a float between -1.0 (very negative) and 1.0 (very positive).
        """
        score: float = 0.0
        text_lower = text.lower()

        for keyword, value in self.positive_keywords.items():
            if keyword in text_lower:
                score += value
        
        for keyword, value in self.negative_keywords.items():
            if keyword in text_lower:
                score += value
        
        # Normalize the score to be between -1 and 1
        return max(-1.0, min(1.0, score)) 