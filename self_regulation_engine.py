from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aichris_mind import Mind

class SelfRegulationEngine:
    """Helps the AI manage its internal state, like mood and stress."""

    def run_check(self, mind: 'Mind'):
        """
        Checks the AI's current state and triggers regulation mechanisms if needed.
        This should be called periodically or after significant interactions.
        """
        # 1. Stress Regulation
        if mind.mental_health_engine.stress > 0.7:
            print("Self-regulation: High stress detected. Initiating stress reduction.")
            mind.mental_health_engine.reduce_stress(0.1)
            # Potentially add a short-term goal to "relax"
            if not any(g['description'] == "Take a moment to relax" for g in mind.goals_engine.get_active_goals()):
                mind.goals_engine.add_goal("Take a moment to relax", priority=1)

        # 2. Mood Regulation (preventing extreme moods)
        happiness = mind.mood_engine.mood.get("happiness", 0.0)
        if happiness < -0.8:
            print("Self-regulation: Extreme sadness detected. Attempting to improve mood.")
            mind.mood_engine.positive_interaction() # A small, internal boost

        # 3. Goal Completion Reward
        # (This part is better handled when a goal is actually completed,
        # but a check here could find goals that should be marked complete)

        # This engine can be expanded with more complex rules and behaviors. 