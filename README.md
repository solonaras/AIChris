# AIChris
Ai Chris is a privately made ai chatbot and assistant. that still needs a lot of work.
AI Chris Bot
Welcome to the AI Chris Bot repository! This is a multifunctional Discord bot built with Python, featuring natural language processing, text-to-speech (TTS), music playback, Wikipedia lookups, and YouTube live chat monitoring using the YouTube Data API.
Features

Chat with AI: Engage in natural conversations using a local LLM (via Ollama) with a fallback TinyLlama model.
Text-to-Speech (TTS): Customize male voices (e.g., David, Mark) and control rate and volume for voice responses.
Music Player: Play YouTube audio streams in Discord voice channels with queue support.
Wikipedia Lookup: Fetch summaries from Wikipedia for any topic.
YouTube Chat Monitoring: Monitor and respond to live YouTube chat using OAuth 2.0 authentication.
Memory System: Store conversation history and user preferences in a SQLite database.
Role Customization: Set the bot's role (e.g., YouTube streamer) to tailor its responses.

Prerequisites

Python 3.8+
FFmpeg: Required for audio processing (download from ffmpeg.org and add to PATH).
Ollama: For local LLM support (install from ollama.ai and pull the aichris:latest model).
Google Cloud Credentials: A client_secrets.json file for YouTube API authentication (see setup below).
Discord Bot Token: Obtain from the Discord Developer Portal.

Setup Instructions
1. Clone the Repository
git clone https://github.com/yourusername/ai-chris-bot.git
cd ai-chris-bot

2. Create a Virtual Environment
python -m venv venv
venv\Scripts\activate  # On Windows

3. Install Dependencies
pip install discord.py torch transformers yt-dlp pyttsx3 ollama requests beautifulsoup4 google-api-python-client google-auth-oauthlib

4. Configure Google Cloud for YouTube API

Create a project in the Google Cloud Console.
Enable the YouTube Data API under "APIs & Services" > "Library".
Go to "Credentials", create an OAuth 2.0 Client ID (Desktop app), and download client_secrets.json.
Place client_secrets.json in the project directory.

5. Set Up Discord Bot

Create a bot in the Discord Developer Portal.
Copy the bot token and replace the TOKEN variable in chris_bot.py.
Invite the bot to your server with the necessary permissions (e.g., message content, voice).

6. Start Ollama

Ensure Ollama is running locally (http://localhost:123456). put your own local host.
Pull the aichris:latest model:ollama pull aichris:latest



7. Run the Bot
python chris_bot.py

Commands

!setttsvoice [voice_name] [rate] [volume] - Set TTS voice (e.g., !setttsvoice David 200 1.0).
!listttsvoices - List available male TTS voices.
!setrole <role> - Set the bot's role (e.g., !setrole YouTube streamer).
!clearhistory - Clear your conversation history.
!addknowledge <question> | <answer> - Add to knowledge base (Trusted role only).
!lookup <term> - Look up a term on Wikipedia.
!startytchatdirect <video_id> - Monitor YouTube live chat (e.g., !startytchatdirect stream id).
!join - Join your voice channel.
!play <YouTube URL> - Play music.
!queue - Show music queue.
!pause, !resume, !stop, !leave - Music controls.
Chat naturally (e.g., "hello", "how are you?").

Troubleshooting

Missing client_secrets.json: Download it from Google Cloud Console and place it in the project directory.
Import Errors: Ensure all dependencies are installed in the virtual environment.
FFmpeg Not Found: Add FFmpeg to your system PATH.
Ollama Issues: Verify Ollama is running and the model is pulled.

Contributing
Feel free to fork this repository, submit issues, or pull requests to improve the bot!
License
- See the LICENSE file for details.
