# AI Chris - Changelog

This file tracks major updates and new features for the AI Chris application.

## Version 3.0 - The Cognitive Leap (Current)

This major update focuses on giving AI Chris a rich, dynamic, and self-aware personality.

### Key Features:

-   **Advanced Cognitive Loop**: The AI now follows a sophisticated cognitive cycle: it analyzes user emotion, updates its internal state, performs self-regulation, generates a response, and then journals the interaction for long-term memory.
-   **Full Personality Engines**:
    -   `MoodEngine`: Tracks and modulates the AI's mood.
    -   `TrustEngine`: Manages trust levels with individual users.
    -   `GoalsEngine`: Allows the AI to have and track its own goals.
    -   `PsychologicalEngine`: Models long-term personality traits (Big Five) and cognitive biases.
    -   `MentalHealthEngine`: Monitors stress and burnout to maintain operational stability.
    -   `UserProfileEngine`: Creates and maintains persistent profiles for users it interacts with.
-   **Self-Awareness & Regulation**:
    -   `PerformanceMonitor`: Actively tracks the success and failure of key operations (API calls, TTS, etc.).
    -   `SelfRegulationEngine`: Periodically checks the AI's internal state and makes adjustments to maintain balance.
    -   `DashboardEngine`: Provides a consolidated, real-time view of all internal states via the `/dashboard` command.
-   **Advanced Communication**:
    -   `ResponseEngine`: Centralizes and streamlines the construction of complex, context-aware prompts.
    -   `VoiceModulationEngine`: Dynamically adjusts voice pitch, rate, and volume based on the AI's current mood.
    -   **Voice Commands**: Added the ability to process natural language commands during voice calls (e.g., "prepare for streaming", "send a dm").
-   **Memory & Reflection**:
    -   `JournalingEngine`: Provides long-term, structured memory of conversations, dreams, and reflections.
    -   The AI can now have periodic "dreams" and "reflections" to process information.

### Bug Fixes:

-   Resolved a startup `TimeoutError` by making personality generation non-blocking.
-   Fixed `discord.errors.ConnectionClosed` by advising a token reset.
-   Addressed various `SyntaxError` and `AttributeError` issues during development.
-   **Bug Fix:** Addressed a UI freeze that occurred when the AI was generating very long responses by moving the response generation to a background thread.
-   **Bug Fix:** Fixed an issue where the AI would sometimes repeat itself in conversation.
-   **UI:** The main chat window now automatically scrolls to the bottom for new messages.

## Version 2.2: The Companion Update

This update focuses on enhancing the AI's ability to interact with users and provide a more seamless experience.

### Key Features:

-   **Enhanced User Interaction**:
    -   `ResponseEngine`: Improved the AI's ability to understand and respond to user inputs.
    -   `VoiceModulationEngine`: Enhanced voice modulation capabilities to better match the AI's emotional state.
    -   **Voice Commands**: Added more natural language commands to improve interaction.
-   **Memory & Reflection**:
    -   `JournalingEngine`: Improved the AI's ability to remember and reflect on past interactions.
    -   The AI can now have periodic "dreams" and "reflections" to process information.

### Bug Fixes:

-   Addressed various `SyntaxError` and `AttributeError` issues during development. 