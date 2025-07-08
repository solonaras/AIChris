from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from aichris_mind import Mind

class VoiceModulationEngine:
    """Manages the AI's voice characteristics based on its internal state."""

    def get_voice_settings(self, mind: 'Mind') -> Dict[str, str]:
        """
        Returns a dictionary with voice settings (pitch, rate, volume)
        based on the AI's mood and stress levels.
        """
        mood_value = mind.mood_engine.mood_value # -1 to 1
        stress, _ = mind.mental_health_engine.get_stress_levels() # 0 to 1

        # --- Pitch Modulation (based on mood) ---
        # Mood range: -1 (sad) to 1 (happy)
        # Pitch range: -20Hz (low) to +20Hz (high)
        pitch_change = int(mood_value * 20)
        pitch = f"+{pitch_change}Hz" if pitch_change >= 0 else f"{pitch_change}Hz"

        # --- Rate Modulation (based on stress) ---
        # Stress range: 0 (calm) to 1 (stressed)
        # Rate range: -10% (slower) to +25% (faster)
        # Calm speech is normal rate, high stress is faster.
        rate_change = int(stress * 25)
        rate = f"+{rate_change}%"

        # --- Volume Calculation ---
        # Higher excitement = louder, Lower happiness (sadness) = quieter
        volume_adjustment = (mood_value * 20) + (mood_value * 10)
        volume = f"{max(-50, min(50, volume_adjustment)):+.0f}%"
        
        print(f"Voice settings generated: Pitch={pitch}, Rate={rate}, Volume={volume}")

        return {
            "pitch": pitch,
            "rate": rate,
            "volume": volume
        } 