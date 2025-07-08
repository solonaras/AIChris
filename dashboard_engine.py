from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from aichris_mind import Mind

class DashboardEngine:
    """Provides a consolidated view of the AI's entire internal state."""

    def get_dashboard_report(self, mind: 'Mind', user_id: str, username: str) -> str:
        """
        Gathers data from all engines and formats it into a single text block
        to be used as context for the LLM.
        """
        # User-specific data
        user_profile = mind.user_profile_engine.get_or_create_profile(user_id, username)
        trust_level = mind.trust_engine.get_trust(user_id)

        # General internal state
        mood = mind.mood_engine.get_mood_description()
        stress, burnout = mind.mental_health_engine.get_stress_levels()
        goals = mind.goals_engine.get_active_goals_string()
        psych_traits = mind.psychological_engine.get_traits_summary()
        biases = mind.psychological_engine.get_active_biases_summary()
        beliefs = mind.core_beliefs.get_all_as_string()
        values = mind.core_values.get_all_as_string()
        agent_statement = mind.knowledge_base.get_agent_statement()
        knowledge = mind.knowledge_base.get_all_as_string()
        age_report = mind.aging_engine.get_age_report()
        dynamic_traits = mind.psychological_engine.get_dynamic_traits_summary()

        report = f"""
# Agent Identity
{agent_statement}
{age_report}

---
## AI Internal State Dashboard
This is a snapshot of my current internal state. Use it to inform your response.

### Core Values
{values}

### Core Beliefs
{beliefs}

### Dynamic Personality Traits
{dynamic_traits}

### Current Psychological State
- **Mood**: {mood}
- **Stress Level**: {stress:.2f}/1.0
- **Burnout Level**: {burnout:.2f}/1.0
- **Active Cognitive Biases**: {biases}

### System Performance
- **Live Diagnostics**: {mind.system_monitor.get_report_string()}
- **Operational Summary**: {mind.performance_monitor.get_performance_summary()}

### Active Goals
{goals}

### Relationship with Current User ({username})
- **Trust Level**: {trust_level:.2f}/1.0
- **User Profile Summary**: {user_profile.get_summary()}

### Foundational Personality Traits (Big Five)
{psych_traits}
"""
        return report.strip()

    def get_structured_dashboard(self, mind: 'Mind', user_id: str, username: str) -> Dict[str, Any]:
        """Returns the dashboard state as a structured dictionary."""
        user_profile = mind.user_profile_engine.get_or_create_profile(user_id, username)
        
        dashboard = {
            "internal_state": {
                "mood": mind.mood_engine.mood,
                "mood_description": mind.mood_engine.get_mood_description(),
                "mental_health": {
                    "stress": mind.mental_health_engine.stress,
                    "burnout": mind.mental_health_engine.burnout,
                },
                "psychology": mind.psychological_engine.personality,
            },
            "user_context": {
                "user_id": user_id,
                "username": username,
                "trust_level": mind.trust_engine.get_trust(user_id),
                "profile_notes": user_profile.notes,
            },
            "objectives": {
                "active_goals": mind.goals_engine.get_active_goals(),
            },
            "performance": mind.performance_monitor.get_event_summary(),
        }
        return dashboard 