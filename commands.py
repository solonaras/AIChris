# ommands.py
# This file will hold all the text and voice commands for AI Chris.
#
# Voice commands now support arguments. The system will listen for a command
# phrase (e.g., "play", "tweet", "website") and treat the rest of the
# spoken text as arguments for that command.
#
# Examples of voice commands:
# - "play https://www.youtube.com/watch?v=dQw4w9WgXcQ"
# - "tweet This is a test tweet from AI Chris!"
# - "website google.com"
# - "dm 123456789 Hello there!"

# open obs

# open discord

# open twitch

# open youtube

# open twitter

# open facebook

# open instagram

# open tiktok

# join call discord

# play a song youtube url

# skip song

# pause song

# resume song

# stop song

# leave call discord

# join twitch channel

# leave twitch channel

# join youtube channel

# leave youtube channel

# post a tweet

# post a facebook post

# post a instagram post

# post a tiktok post

# send dm to a user in my discord servers, and they can reply to me in my dm, and i can reply to them in my dm

# open a website

# open a youtube video

# open whatsapp desktop

# write a song

# write a poem

# open gmail

import webbrowser
import subprocess
from typing import TYPE_CHECKING
import threading
import asyncio

if TYPE_CHECKING:
    from main import ChatBot

class CommandHandler:
    """Handles all text and voice commands for AI Chris."""
    def __init__(self, chatbot: 'ChatBot'):
        self.chatbot = chatbot

        # Voice commands are now primarily for actions without arguments.
        # Argument-based commands are handled by the text_commands logic.
        self.voice_commands = {
            "open obs": self.open_obs,
            "open discord": lambda: self.open_website("https://discord.com/app"),
            "open twitch": lambda: self.open_website("https://twitch.tv/solonaras"),
            "open youtube": lambda: self.open_website("https://youtube.com/solonaras"),
            "open twitter": lambda: self.open_website("https://twitter.com/chrisSolonos"),
            "open facebook": lambda: self.open_website("https://facebook.com/solonaras"),
            "open instagram": lambda: self.open_website("https://instagram.com/solonarass"),
            "open tiktok": lambda: self.open_website("https://tiktok.com/christossolonos"),
            "open whatsapp": self.open_whatsapp,
            "open gmail": lambda: self.open_website("https://gmail.com"),
            "join call": self.join_discord_call,
            "leave call": self.leave_discord_call,
            "skip song": self.skip_song,
            "pause song": self.pause_song,
            "resume song": self.resume_song,
            "stop song": self.stop_song,
        }

        # Maps text commands (e.g., /play) to their corresponding methods
        # These are now also used as the primary triggers for voice commands with arguments.
        self.text_commands = {
            "help": self.show_help,
            "play": self.play_song,
            "playlocal": self.play_local_music,
            "skip": self.skip_song,
            "pause": self.pause_song,
            "resume": self.resume_song,
            "stop": self.stop_song,
            "dm": self.send_discord_dm,
            "tweet": self.post_tweet,
            "post": self.post_to_social,
            "website": self.open_website_from_arg,
            "video": self.open_youtube_video,
            "song": self.write_song,
            "poem": self.write_poem,
            "add_twitch_channel": self.add_twitch_channel,
            "remove_twitch_channel": self.remove_twitch_channel,
            "suno": self.play_suno_song,
        }

    def _execute_and_respond(self, message: str):
        """Helper to append a message to the chat display via a signal."""
        self.chatbot.append_text_signal.emit(message)

    def _run_in_thread(self, target_func):
        """Helper to run a function in a daemon thread."""
        threading.Thread(target=target_func, daemon=True).start()

    def _generate_creative_content(self, prompt: str, title: str):
        """Generic function to generate content from the AI mind."""
        def do_generation():
            content = self.chatbot.get_generic_ai_response(prompt)
            # Format the response nicely in the chat window
            html_content = f"""
            <div style='background-color: #282a36; color: #f8f8f2; padding: 15px; border-left: 5px solid #bd93f9; margin: 10px 0; border-radius: 5px;'>
                <h4 style='margin-top: 0; color: #ff79c6;'>{title}</h4>
                <p style='white-space: pre-wrap; font-family: monospace;'>{content}</p>
            </div>
            """
            self._execute_and_respond(html_content)

        self._run_in_thread(do_generation)
        self._execute_and_respond(f"<b style=\"color:#ffb86c\">System:</b> I'm working on that {title.lower()} for you...")

    # --- Voice Command Implementations ---
    
    def open_obs(self):
        """Opens the OBS application."""
        try:
            # This path may need to be adjusted based on the user's system
            obs_path = "C:\\Program Files\\obs-studio\\bin\\64bit\\obs64.exe"
            subprocess.Popen([obs_path])
            self._execute_and_respond("<b style=\"color:#ffb86c\">System:</b> Opening OBS...")
        except FileNotFoundError:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> OBS not found. Please check the path in commands.py.")
        except Exception as e:
            self._execute_and_respond(f"<b style=\"color:#ff5555\">Error:</b> Failed to open OBS: {e}")

    def open_website(self, url: str):
        """Opens a website in the default browser."""
        try:
            webbrowser.open(url)
            self._execute_and_respond(f"<b style=\"color:#ffb86c\">System:</b> Opening {url}...")
        except Exception as e:
            self._execute_and_respond(f"<b style=\"color:#ff5555\">Error:</b> Failed to open website: {e}")
    
    def open_whatsapp(self):
        """Opens the WhatsApp desktop application."""
        try:
            subprocess.Popen("start whatsapp:", shell=True)
            self._execute_and_respond("<b style=\"color:#ffb86c\">System:</b> Opening WhatsApp...")
        except Exception as e:
            self._execute_and_respond(f"<b style=\"color:#ff5555\">Error:</b> Failed to open WhatsApp: {e}")

    def join_discord_call(self):
        """Sends a command to the Discord bot to join a voice call."""
        self._execute_and_respond("<b style=\"color:#ffb86c\">System:</b> Sending command to join Discord voice channel...")
        self.chatbot.send_to_discord("!join")

    def leave_discord_call(self):
        """Sends a command to the Discord bot to leave a voice call."""
        self._execute_and_respond("<b style=\"color:#ffb86c\">System:</b> Sending command to leave Discord voice channel...")
        self.chatbot.send_to_discord("!leave")

    # --- Text Command Implementations ---

    def show_help(self, args: list):
        """Displays the list of available commands."""
        # Dynamically generate help text from the command map
        commands_list = "<br>".join([f"/{cmd}" for cmd in self.text_commands.keys()])
        help_text = f"<b style=\"color:#ffb86c\">Available Commands:</b><br>{commands_list}"
        self._execute_and_respond(help_text)

    def play_song(self, args: list):
        """Plays a song from a URL or search term."""
        if args:
            url_or_term = " ".join(args)
            self._execute_and_respond(f"<b style=\"color:#ffb86c\">System:</b> Playing: {url_or_term}...")
            self.chatbot.send_to_discord(f"!play {url_or_term}")
        else:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Please provide a URL or search term. Usage: /play [url or term]")

    def skip_song(self, args: list = None):
        """Skips the current song in the Discord music queue."""
        self._execute_and_respond("<b style=\"color:#ffb86c\">System:</b> Skipping song...")
        self.chatbot.send_to_discord("!skip")

    def pause_song(self, args: list = None):
        """Pauses the current song."""
        self._execute_and_respond("<b style=\"color:#ffb86c\">System:</b> Pausing song...")
        self.chatbot.send_to_discord("!pause")

    def resume_song(self, args: list = None):
        """Resumes the current song."""
        self._execute_and_respond("<b style=\"color:#ffb86c\">System:</b> Resuming song...")
        self.chatbot.send_to_discord("!resume")

    def stop_song(self, args: list = None):
        """Stops the music and clears the queue."""
        self._execute_and_respond("<b style=\"color:#ffb86c\">System:</b> Stopping music...")
        self.chatbot.send_to_discord("!stop")

    def send_discord_dm(self, args: list):
        """Sends a direct message to a Discord user."""
        if len(args) >= 2:
            recipient = args[0]
            message = " ".join(args[1:])
            self._execute_and_respond(f"<b style=\"color:#ffb86c\">System:</b> Sending DM to {recipient}...")
            # Note: The !dm command in discord_bot.py is restricted to the owner.
            self.chatbot.send_to_discord(f"!dm {recipient} {message}")
        else:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Usage: /dm [user_id] [message]")

    def open_website_from_arg(self, args: list):
        """Opens a website from an argument."""
        if args:
            url = args[0]
            # A basic check to ensure a protocol is present.
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            self.open_website(url)
        else:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Please provide a URL. Usage: /website [url]")

    def open_youtube_video(self, args: list):
        """Opens a YouTube video in the browser."""
        if args:
            video_url = args[0]
            self.open_website(video_url)
        else:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Please provide a video URL. Usage: /video [url]")

    def write_song(self, args: list):
        """Writes a song based on a prompt."""
        if not args:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Please provide a topic for the song. Usage: /song [topic]")
            return
        topic = " ".join(args)
        prompt = f"Write a complete song about '{topic}'. The song should have a clear structure, such as verses, a chorus, and a bridge."
        self._generate_creative_content(prompt, f"Song about {topic}")
        
    def write_poem(self, args: list):
        """Writes a poem based on a prompt."""
        if not args:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Please provide a topic for the poem. Usage: /poem [topic]")
            return
        topic = " ".join(args)
        prompt = f"Write a thoughtful and evocative poem about '{topic}'."
        self._generate_creative_content(prompt, f"Poem about {topic}")

    # --- Social Media & Advanced Command Placeholders ---

    def post_tweet(self, args: list):
        """
        Posts a tweet to Twitter.
        NOTE: This is a placeholder. To implement this, you would need:
        1. A Twitter Developer account and API keys (consumer key, secret, access token, secret).
        2. A library like 'tweepy' (`pip install tweepy`).
        3. A secure way to store and access your credentials.
        """
        content = " ".join(args)
        if not content:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Please provide content for the tweet.")
            return
        self._execute_and_respond(f"<b style=\"color:#ffb86c\">System:</b> Tweet prepared: '{content}'.<br><i>(Integration not yet complete. API keys required.)</i>")

    def post_to_social(self, args: list):
        """
        Posts to a specified social media platform.
        NOTE: This is a complex placeholder. Implementation would require:
        1. Separate API credentials for each platform (Facebook, Instagram, etc.).
        2. The specific SDK/library for each platform.
        3. Handling different content types (text, images, videos).
        """
        if len(args) < 2:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Usage: /post [platform] [content]")
            return
        platform = args[0]
        content = " ".join(args[1:])
        self._execute_and_respond(f"<b style=\"color:#ffb86c\">System:</b> Post for {platform} prepared: '{content}'.<br><i>(Platform integration not yet complete. API keys required.)</i>")

    def add_twitch_channel(self, args: list):
        """
        Adds a Twitch channel for the bot to monitor.
        NOTE: This is a placeholder. Implementation requires a running Twitch bot instance
        that can dynamically join new channels.
        """
        if not args:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Please provide a channel name.")
            return
        channel_name = args[0]
        self._execute_and_respond(f"<b style=\"color:#ffb86c\">System:</b> Command to join Twitch channel '{channel_name}' received.<br><i>(Twitch integration for dynamic channel joining is not yet complete.)</i>")

    def remove_twitch_channel(self, args: list):
        """Removes a twitch channel from the bot's list."""
        if args:
            channel_name = args[0]
            # This is a placeholder for the actual logic to remove a channel
            self._execute_and_respond(f"<b style=\"color:#ffb86c\">System:</b> Removing Twitch channel: {channel_name}")
            # self.chatbot.twitch_bot.remove_channel(channel_name)
        else:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Please provide a channel name. Usage: /remove_twitch_channel [name]")
            
    def play_suno_song(self, args: list):
        """Plays a song from a Suno URL."""
        if args:
            url = args[0]
            self._execute_and_respond(f"<b style=\"color:#ffb86c\">System:</b> Playing Suno song from {url}...")
            self.chatbot.send_to_discord(f"!suno {url}")
        else:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Please provide a Suno URL. Usage: /suno [url]")

    def play_local_music(self, args: list):
        """Plays a local music file (mp3, wav, etc.) from the user's PC."""
        import os
        try:
            import pygame
        except ImportError:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Pygame is not installed. Please install it with: pip install pygame")
            return

        if not args:
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Please provide a file path. Usage: /playlocal [filepath]")
            return
        filepath = " ".join(args)
        if not os.path.isfile(filepath):
            self._execute_and_respond(f"<b style=\"color:#ff5555\">Error:</b> File not found: {filepath}")
            return
        if not filepath.lower().endswith((".mp3", ".wav", ".ogg", ".flac")):
            self._execute_and_respond("<b style=\"color:#ff5555\">Error:</b> Unsupported file type. Supported: mp3, wav, ogg, flac.")
            return

        def play_music():
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.load(filepath)
                pygame.mixer.music.play()
                self._execute_and_respond(f"<b style=\"color:#ffb86c\">System:</b> Playing local file: {filepath}")
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                self._execute_and_respond(f"<b style=\"color:#ffb86c\">System:</b> Finished playing: {filepath}")
            except Exception as e:
                self._execute_and_respond(f"<b style=\"color:#ff5555\">Error:</b> Could not play file: {e}")
        self._run_in_thread(play_music)



