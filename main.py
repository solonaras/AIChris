import re
import sys
import requests
import os
import json
import webbrowser
import subprocess
import tempfile
import threading
import time
import asyncio
import edge_tts
import random
import sounddevice as sd
import numpy as np
import noisereduce as nr
import io
import queue
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from moviepy.editor import AudioFileClip
from moviepy.video.VideoClip import ColorClip, TextClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
import textwrap
from typing import Tuple
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QLabel, QHBoxLayout, QGridLayout
)
from PyQt5.QtGui import QFont, QColor, QPalette, QTextCursor
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from mutagen.mp3 import MP3
from avatar import AvatarWindow, AVATAR_CLOSED_PATH, AVATAR_OPEN_PATH
import websocket
import webrtcvad
from twitch import TwitchChatBot
import discord_bot
import web_server
from aichris_mind import Mind
from database_engine import DatabaseEngine
from commands import CommandHandler

# Add this near the top of the file with other constants
CHATBOT_STATE_FILE = "chatbot_state.json"
CHATBOT_SUMMARY_KEY = "main_gui_summary"
DISCORD_COMMAND_CHANNEL_ID = "1387208152029859860"  # Same as in discord_bot.py

# Set ffmpeg path for Whisper
ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg-2025-03-24-git-cbbc927a67-essentials_build", "bin", "ffmpeg.exe")
os.environ["PATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg-2025-03-24-git-cbbc927a67-essentials_build", "bin") + os.environ["PATH"]
os.environ["FFMPEG_PATH"] = ffmpeg_path
print(f"FFMPEG path set to: {ffmpeg_path}")
import whisper

LONG_TERM_MEMORY_FILE = "memory.jsonl"
SHORT_TERM_MEMORY_LIMIT = 10
# OLLAMA_URL is now configured via .env and used by the bridge/bots directly if needed
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = "nemotron-mini:4b"
# Discord functionality is now handled by the app.js bridge
# DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/your_webhook_id/your_webhook_token"
# DISCORD_COMMAND_CHANNEL_ID = "your_channel_id"

# Global variable to track file modification time for automatic reloading
watched_files = {} # Use a dictionary to track multiple files

class ChatBot(QWidget):
    append_text_signal = pyqtSignal(str)
    append_thinking_signal = pyqtSignal(str)
    append_reflection_signal = pyqtSignal(str)
    append_dream_signal = pyqtSignal(str)
    append_knowledge_signal = pyqtSignal(str)
    append_evolution_signal = pyqtSignal(str)
    append_mood_signal = pyqtSignal(str)
    append_trust_signal = pyqtSignal(str)
    append_user_profile_signal = pyqtSignal(str)
    append_mental_health_signal = pyqtSignal(str)
    append_goals_signal = pyqtSignal(str)
    update_status_signal = pyqtSignal(str)
    restart_mind_timer_signal = pyqtSignal(int)

    def __init__(self, model_id: str, db_engine: DatabaseEngine):
        super().__init__()
        self.db = db_engine
        
        # Initialize variables
        self.conversation_history = []
        self.short_term_memory = []
        self.long_term_memory = []
        self.long_term_summary = "No conversation history yet."
        self.last_dream = "Awaiting new dreams..."
        self.last_reflection = "Awaiting new self-reflections..."
        self.model_id = model_id
        self.mind = Mind(model_id=self.model_id, db_engine=self.db, chatbot_ui=self)
        self.last_performance_summary = "No analysis yet."
        self.command_handler = CommandHandler(self)
        
        # Load previous state from DB
        self.load_state()
        
        self.tts_voice = "en-US-ChristopherNeural"
        self.message_queue = queue.Queue()
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self.current_text = ""
        self.syllable_count = 0
        self.syllable_index = 0
        self.is_recording = False
        self.last_twitch_message_time = time.time()
        self.action_log = []
        self.additional_twitch_channels = []
        self.pending_dm_recipient = None  # For the "send dm" voice command
        
        # New state for voice call mode
        self.is_in_voice_call_mode = False
        self.voice_call_thread = None
        
        # Pre-compile regex patterns for efficiency
        self.emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F700-\U0001F77F"  # alchemical symbols
            "\U0001F780-\U0001F7FF"  # Geometric Shapes
            "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
            "\U0001FA00-\U0001FA6F"  # Chess Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "\U00002702-\U000027B0"  # Dingbats
            "\U000024C2-\U0001F251" 
            "]+", flags=re.UNICODE
        )
        self.url_pattern = re.compile(r'https?://\S+|www\.\S+')
        self.markdown_link_pattern = re.compile(r'\[([^\]]+)\]\([^)]+\)')
        self.bracket_link_pattern = re.compile(r'\[[^\]]+\]\([^)]+\)')
        self.hashtag_pattern = re.compile(r'#\w+')

        # Create folders for generated content if they don't exist
        self.generated_videos_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated_videos")
        self.quote_images_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quote_images")
        self.web_audio_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_ui", "audio")
        
        # Create folders if they don't exist
        os.makedirs(self.generated_videos_folder, exist_ok=True)
        os.makedirs(self.quote_images_folder, exist_ok=True)
        os.makedirs(self.web_audio_folder, exist_ok=True)
        
        # Connect signals
        self.append_text_signal.connect(self._on_append_text)
        self.append_thinking_signal.connect(self._on_append_thinking)
        self.append_reflection_signal.connect(self._on_append_reflection)
        self.append_dream_signal.connect(self._on_append_dream)
        self.append_knowledge_signal.connect(self._on_append_knowledge)
        self.append_evolution_signal.connect(self._on_append_evolution)
        self.append_mood_signal.connect(self._on_append_mood)
        self.append_trust_signal.connect(self._on_append_trust)
        self.append_user_profile_signal.connect(self._on_append_user_profile)
        self.append_mental_health_signal.connect(self._on_append_mental_health)
        self.append_goals_signal.connect(self._on_append_goals)
        self.update_status_signal.connect(self._on_update_status)
        self.restart_mind_timer_signal.connect(self._on_restart_mind_timer)
        
        # Load avatar
        self.avatar_window = AvatarWindow("chris avatar cropped.png", "Aichrisopenmouth.png")
        self.avatar_window.show()

        # Start the dedicated asyncio event loop thread first
        self.async_loop = asyncio.new_event_loop()
        threading.Thread(target=self.start_async_loop, daemon=True).start()

        # Set up UI
        self.init_ui()
        
        # Initialize TTS
        self.init_tts()
        
        # The Discord bot is initialized separately and runs in its own thread.
        self.init_discord_bot()
        
        # The Web Server is initialized separately and runs in its own thread.
        self.init_web_server()
        
        # Start message queue processor
        threading.Thread(target=self.process_message_queue, daemon=True).start()
        
        # Start speech queue processor
        threading.Thread(target=self.process_speech_queue, daemon=True).start()
        
        # Load Whisper model in a separate thread
        threading.Thread(target=self.load_whisper_model, daemon=True).start()
        
        # Set up timers for various periodic tasks
        # Check for code changes every 5 seconds
        self.check_code_changes(init=True)
        self.code_check_timer = QTimer(self)
        self.code_check_timer.timeout.connect(lambda: self.check_code_changes())
        self.code_check_timer.start(5000)
        
        # New timer for the mind/dream cycle
        self.mind_cycle_timer = QTimer(self)
        self.mind_cycle_timer.timeout.connect(self.run_mind_cycle)
        # Start with a random delay, then run every 2-4 minutes
        self.mind_cycle_timer.start(random.randint(20, 45) * 1000)
        
        # New timer for the performance analysis cycle
        self.awareness_cycle_timer = QTimer(self)
        self.awareness_cycle_timer.timeout.connect(self.run_awareness_cycle)
        self.awareness_cycle_timer.start(300 * 1000) # Run every 5 minutes
        
        # New timer for refreshing passive UI elements like mood and trust
        self.ui_update_timer = QTimer(self)
        self.ui_update_timer.timeout.connect(self.update_passive_ui)
        self.ui_update_timer.start(15000) # Update every 15 seconds
        
        # Initialize last activity time
        self.last_activity_time = time.time()
        self.is_in_conversation = False

    def closeEvent(self, event):
        """Handles the window closing event to save the final summary."""
        print("Stopping all timers...")
        self.code_check_timer.stop()
        self.mind_cycle_timer.stop()
        self.awareness_cycle_timer.stop()
        self.ui_update_timer.stop()

        print("Saving final summary before closing...")
        self.save_state()
        self.db.close() # Close the database connection
        super().closeEvent(event)

    def load_state(self):
        """Loads the chatbot's state from the database."""
        # Try to migrate old JSON file first
        self.run_migration_from_json()

        self.conversation_history = self.db.load_chat_history(channel="main_gui")
        summary_state = self.db.load_system_state(CHATBOT_SUMMARY_KEY)
        if summary_state:
            self.long_term_summary = summary_state.get("summary", "No conversation history yet.")
        
        dream_state = self.db.load_system_state("last_dream")
        if dream_state:
            self.last_dream = dream_state.get("content", self.last_dream)
        
        reflection_state = self.db.load_system_state("last_reflection")
        if reflection_state:
            self.last_reflection = reflection_state.get("content", self.last_reflection)

        print(f"Loaded {len(self.conversation_history)} messages from chat history.")

    def save_state(self):
        """Saves the final long-term summary to the database."""
        # This function is now a no-op as state is saved continuously.
        # The final summary generation is removed to prevent persona leakage.
        print("Close event triggered. State is already saved continuously to the database.")

    def start_async_loop(self):
        """Runs the asyncio event loop in a dedicated thread."""
        asyncio.set_event_loop(self.async_loop)
        self.async_loop.run_forever()

    def _on_restart_mind_timer(self, delay):
        """Thread-safe method to restart the mind cycle timer."""
        self.mind_cycle_timer.start(delay)

    def run_awareness_cycle(self):
        """Periodically analyzes performance and updates the AI's context."""
        print("Running self-awareness cycle...")
        summary = self.mind.performance_monitor.get_performance_summary()
        self.last_performance_summary = summary
        
        # Display the analysis in the UI
        self.append_text_signal.emit(f"<i style=\"color:#4d88ff;\">System Analysis: {summary}</i>")

    def run_mind_cycle(self):
        """Periodically generates a reflection or a dream."""
        self.append_text_signal.emit("<i style=\"color:#44475a;\">[Mind cycle triggered...]</i>")
        # Don't have internal thoughts if currently busy
        if self.is_speaking or self.is_in_conversation or self.is_in_voice_call_mode:
            self.mind_cycle_timer.start(random.randint(60, 90) * 1000) # Reschedule sooner if busy
            return

        # Decide what to do in the mind cycle
        action_roll = random.random()

        # 5% chance to consider evolving core values
        if action_roll < 0.05 and self.conversation_history:
            coro = self.mind.core_values.evolve(self.mind, self.conversation_history)
        # 5% chance to evolve dynamic traits
        elif action_roll < 0.10 and self.conversation_history:
            coro = self.mind.psychological_engine.evolve_dynamic_traits(self.mind, self.conversation_history)
        # 10% chance to consider evolving beliefs if there's history
        elif action_roll < 0.20 and self.conversation_history:
            coro = self.mind.consider_belief_evolution(self.conversation_history)
        # 15% chance to extract new knowledge from the conversation
        elif action_roll < 0.35 and self.conversation_history:
            coro = self.mind.knowledge_base.extract_and_learn(self.mind, self.conversation_history)
        # 35% chance to reflect on recent topics
        elif action_roll < 0.70 and self.conversation_history:
             # Reflect on the conversation with the local user
             last_user_message = next((msg for msg in reversed(self.conversation_history) if msg['role'] == 'user'), None)
             topic = last_user_message.get("content", "our recent chat") if last_user_message else "our recent chat"
             coro = self.mind.reflect(topic, 'local_user', 'Local User', self.conversation_history)
        # 30% chance to dream
        else:
            coro = self.mind.dream('local_user', 'Local User', self.conversation_history)

        # Submit the coroutine to the running event loop
        future = asyncio.run_coroutine_threadsafe(coro, self.async_loop)
        
        def on_done(f):
            try:
                result = f.result()
                # Belief evolution returns the new belief as a string if successful
                if isinstance(result, str):
                    thought = result
                    # Determine if it was a dream, reflection, or new belief to display it correctly
                    if "evolve" in str(coro):
                        # Distinguish between belief and value evolution
                        if "core_values" in str(coro):
                             display_text = f"AI Chris has evolved a core value: {thought}"
                             history_text = f"(Value Evolution: {thought})"
                        else:
                            display_text = f"AI Chris has formed a new belief: {thought}"
                            history_text = f"(New Belief: {thought})"
                        self.append_evolution_signal.emit(display_text)
                    elif 'dream' in str(coro):
                        self.append_dream_signal.emit(thought)
                        history_text = f"(Dream: {thought})"
                        self.db.save_system_state("last_dream", {"content": thought})
                    elif 'reflect' in str(coro):
                        self.append_reflection_signal.emit(thought)
                        history_text = f"(Self-reflection: {thought})"
                        self.db.save_system_state("last_reflection", {"content": thought})
                    
                    # Add to conversation history for context, but don't display in main chat
                    self.conversation_history.append({"role": "assistant", "content": history_text})
                    self.save_to_long_term_memory({"monologue": thought, "timestamp": time.time()})

                elif "extract_and_learn" in str(coro):
                    self.append_knowledge_signal.emit("[Knowledge base updated with new information.]")
                elif "evolve_dynamic_traits" in str(coro):
                    self.append_evolution_signal.emit("[Personality traits have shifted based on recent interactions.]")
                else: # No thought/belief generated
                    self.append_thinking_signal.emit("[Mind cycle finished: No significant thought generated.]")

            except Exception as e:
                print(f"Error in mind cycle: {e}")
                self.append_thinking_signal.emit(f"[Mind cycle error: {e}]")
            
            # Safely restart the timer from the main GUI thread
            self.restart_mind_timer_signal.emit(random.randint(120, 240) * 1000)
        
        future.add_done_callback(on_done)

    def stop_tts(self):
        """Stop any currently playing TTS audio"""
        try:
            # This ensures we only try to stop if the mixer is running
            import pygame
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                print("TTS audio stopped.")
        except ImportError:
            # Pygame might not be installed or initialized
            print("Pygame not available, cannot stop TTS.")
        except Exception as e:
            # Catch other potential pygame errors
            print(f"Error stopping TTS: {e}")

    def load_whisper_model(self):
        try:
            import torch
            # Check if CUDA is available and select the device accordingly
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Loading Whisper model on device: {device}")
            
            # Use a more accurate model for better transcription
            self.whisper_model = whisper.load_model("base.en", device=device)
            print("Whisper 'base.en' model loaded successfully.")
            
            if device == "cpu":
                print("Whisper is running on the CPU. For GPU acceleration, ensure you have an NVIDIA GPU and a CUDA-enabled version of PyTorch installed.")
                
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            print("Falling back to CPU for Whisper.")
            # Ensure fallback to CPU if any error occurs
            try:
                self.whisper_model = whisper.load_model("base.en", device="cpu")
                print("Whisper model loaded on CPU after fallback.")
            except Exception as fallback_e:
                print(f"Could not even load Whisper model on CPU: {fallback_e}")
                self.whisper_model = None

    def init_ui(self):
        self.setWindowTitle('AI Chris: The Digital Mind')
        self.setGeometry(50, 50, 1600, 900)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 36))
        palette.setColor(QPalette.Base, QColor(40, 40, 48))
        palette.setColor(QPalette.Text, QColor(220, 220, 220))
        palette.setColor(QPalette.Button, QColor(60, 60, 80))
        palette.setColor(QPalette.ButtonText, QColor(220, 220, 220))
        self.setPalette(palette)

        main_layout = QGridLayout(self)

        # --- Create all mind panels first ---
        thinking_panel, self.thinking_display = self._create_mind_panel("🤔 Thinking")
        reflection_panel, self.reflection_display = self._create_mind_panel("🧘 Reflections")
        dream_panel, self.dream_display = self._create_mind_panel("🌌 Dreams")
        knowledge_panel, self.knowledge_display = self._create_mind_panel("📚 Knowledge")
        evolution_panel, self.evolution_display = self._create_mind_panel("🧬 Evolution")
        mood_panel, self.mood_display = self._create_mind_panel("😊 Mood")
        trust_panel, self.trust_display = self._create_mind_panel("🤝 Trust")
        user_profile_panel, self.user_profile_display = self._create_mind_panel("👤 User Profile")
        mental_health_panel, self.mental_health_display = self._create_mind_panel("🧠 Mental Health")
        goals_panel, self.goals_display = self._create_mind_panel("🎯 Current Goals")

        # --- Left Column ---
        left_column = QVBoxLayout()
        left_column.addWidget(mood_panel)
        left_column.addWidget(trust_panel)
        left_column.addWidget(mental_health_panel)
        left_column.addWidget(user_profile_panel)
        main_layout.addLayout(left_column, 0, 0)

        # --- Right Column ---
        right_column = QVBoxLayout()
        right_column.addWidget(knowledge_panel)
        right_column.addWidget(evolution_panel)
        right_column.addWidget(goals_panel)
        right_column.addWidget(dream_panel)
        main_layout.addLayout(right_column, 0, 2)

        # --- Center Column ---
        center_column = QVBoxLayout()

        top_row_layout = QHBoxLayout()
        top_row_layout.addWidget(thinking_panel)
        top_row_layout.addWidget(reflection_panel)
        center_column.addLayout(top_row_layout)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont('Arial', 10))
        self.chat_display.setStyleSheet("background-color: #282a36; color: #f8f8f2; border: 1px solid #44475a; border-radius: 5px;")
        center_column.addWidget(self.chat_display)

        input_layout = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setFont(QFont('Arial', 10))
        self.input_box.setStyleSheet("background-color: #44475a; color: #f8f8f2; border: 1px solid #6272a4; border-radius: 5px; padding: 5px;")
        self.input_box.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_box)
        self.send_button = QPushButton('Send')
        self.send_button.setStyleSheet("background-color: #6272a4; color: #f8f8f2; border: none; border-radius: 5px; padding: 5px 15px;")
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)
        self.speak_button = QPushButton('Speak 🎤')
        self.speak_button.setStyleSheet("background-color: #50fa7b; color: #282a36; border: none; border-radius: 5px; padding: 5px 15px; font-size: 14px; font-weight: bold;")
        self.speak_button.clicked.connect(self.run_single_voice_interaction)
        input_layout.addWidget(self.speak_button)
        center_column.addLayout(input_layout)

        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #6272a4; font-style: italic;")
        center_column.addWidget(self.status_label)
        
        center_column.setStretch(1, 1)
        main_layout.addLayout(center_column, 0, 1)

        # --- Set Column Stretch Factors ---
        main_layout.setColumnStretch(0, 1)
        main_layout.setColumnStretch(1, 3)
        main_layout.setColumnStretch(2, 1)

        # Welcome message
        # self.announce_startup() is removed

        # Set initial text for panels with loaded state
        self.reflection_display.setText(self.last_reflection)
        self.dream_display.setText(self.last_dream)

    def _create_mind_panel(self, title: str) -> Tuple[QWidget, QTextEdit]:
        """Helper to create a self-contained panel widget (label + text box)."""
        panel_widget = QWidget()
        panel_layout = QVBoxLayout(panel_widget)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(2)

        label = QLabel(title)
        label.setFont(QFont('Arial', 10, QFont.Bold))
        label.setStyleSheet("color: #bd93f9; margin-top: 5px; margin-bottom: 2px;")
        panel_layout.addWidget(label)

        text_box = QTextEdit()
        text_box.setReadOnly(True)
        text_box.setFont(QFont('Courier New', 9))
        text_box.setStyleSheet(
            "background-color: #21222c; color: #9a9ab0; border: 1px solid #44475a; "
            "border-radius: 5px;"
        )
        panel_layout.addWidget(text_box)
        return panel_widget, text_box

    def _adjust_panel_height(self, text_box: QTextEdit):
        """Dynamically adjusts the height of a text box to fit its content."""
        # This is less effective in a complex grid layout, so we will disable it for now
        # and rely on a fixed but generous height.
        pass

    def _on_update_status(self, text):
        """Updates the status label in the UI."""
        self.status_label.setText(text)

    def _append_to_mind_panel(self, text_box: QTextEdit, text: str):
        """Generic helper to append text to a mind panel and add a separator."""
        # Clear the panel if it only contains the placeholder message
        if text_box.toPlainText().startswith("["):
            text_box.clear()
        
        text_box.append(text + "\n" + "-"*40 + "\n")
        text_box.moveCursor(QTextCursor.End)

    def _on_append_thinking(self, text):
        self._append_to_mind_panel(self.thinking_display, text)

    def _on_append_reflection(self, text):
        self._append_to_mind_panel(self.reflection_display, text)

    def _on_append_dream(self, text):
        self._append_to_mind_panel(self.dream_display, text)

    def _on_append_knowledge(self, text):
        self._append_to_mind_panel(self.knowledge_display, text)

    def _on_append_evolution(self, text):
        self._append_to_mind_panel(self.evolution_display, text)

    def _on_append_mood(self, text):
        """Special handler to overwrite the mood panel instead of appending."""
        self.mood_display.clear()
        self.mood_display.setText(text)

    def _on_append_trust(self, text):
        """Special handler to overwrite the trust panel instead of appending."""
        self.trust_display.clear()
        self.trust_display.setText(text)

    def _on_append_user_profile(self, text):
        """Special handler to overwrite the user profile panel."""
        self.user_profile_display.clear()
        self.user_profile_display.setText(text)

    def _on_append_mental_health(self, text):
        """Special handler to overwrite the mental health panel."""
        self.mental_health_display.clear()
        self.mental_health_display.setText(text)

    def _on_append_goals(self, text):
        """Special handler to overwrite the goals panel."""
        self.goals_display.clear()
        self.goals_display.setText(text)

    def _on_append_text(self, text):
        """Handle text being appended to the chat display"""
        self.chat_display.append(text)
        
    def send_message(self):
        """Handle user sending a message via the UI"""
        user_input = self.input_box.text().strip()
        if not user_input:
            return

        self.input_box.clear()
        self.chat_display.append(f"<b style=\"color:#bd93f9\">You:</b> {user_input}") 
        
        # Update the current user display
        self.update_user_profile_ui('local_user', 'Local User')
        
        # Add to conversation history and DB
        self.conversation_history.append({"role": "user", "content": user_input})
        self.db.add_chat_log('local_user', 'Local User', 'user', user_input)
        
        # Reset activity timer
        self.last_activity_time = time.time()

        # Check if this is a pending DM from a voice command
        if hasattr(self, 'pending_dm_recipient') and self.pending_dm_recipient:
            recipient = self.pending_dm_recipient
            self.pending_dm_recipient = None  # Clear the pending recipient
            
            # Send the DM
            self.append_text_signal.emit(f"<b style=\"color:#50fa7b\">Voice Command:</b> Sending DM to {recipient}: {user_input}")
            self.send_to_discord(f"!dm {recipient} {user_input}")
            return

        # Check for commands
        if user_input.startswith("/"):
            self.process_command(user_input)
            # Acknowledge the command's effect on mood/trust
            self.mind.trust_engine.positive_interaction("local_user")
            return

        # Acknowledge the interaction for mood, trust, and user profile
        self.mind.mood_engine.positive_interaction()
        self.mind.trust_engine.positive_interaction("local_user")
        self.mind.user_profile_engine.get_or_create_profile("local_user", "Local User")

        # Generate response in a thread
        def generate_and_process_response():
            response_data = asyncio.run(self.mind.generate_chat_response(
                "local_user", 
                "Local User", 
                user_input,
                self.conversation_history
            ))
            if response_data and "reply" in response_data:
                self.process_bot_response(user_input, response_data)

        threading.Thread(target=generate_and_process_response, daemon=True).start()
        
    def send_to_discord(self, command_str: str):
        """
        Schedules a command to be dispatched by the Discord bot.
        This is thread-safe.
        """
        if not self.async_loop or not self.async_loop.is_running():
            print("Cannot send to Discord, the event loop is not running.")
            return
            
        # The discord bot has its own event loop, which is what we need to schedule on.
        # We can get it from the bot object itself.
        if hasattr(discord_bot, 'bot') and discord_bot.bot.loop:
            coro = discord_bot.dispatch_command(command_str)
            asyncio.run_coroutine_threadsafe(coro, discord_bot.bot.loop)
        else:
            print("Cannot send to Discord, the bot or its event loop is not ready.")

    def send_ai_message(self, message_text):
        """Send a message from AI Chris"""
        if message_text:
            # Add to queue for display and TTS
            self.add_message_to_queue(f"<b style=\"color:#50fa7b\">AI Chris:</b> {message_text}")
            print(f"AI Chris: {message_text}")

    def get_bot_response(self, user_input, is_retry=False):
        """
        This method is now a legacy wrapper. The response generation is handled 
        by the Mind's generate_chat_response method. This can be removed or refactored
        if all call sites are updated.
        """
        # The new primary way to get a response is via the mind, which is now async.
        # This synchronous wrapper is for compatibility with parts of the code
        # that may not be running in an async context.
        future = asyncio.run_coroutine_threadsafe(
            self.mind.generate_chat_response("local_user", "Local User", user_input, self.conversation_history),
            self.async_loop
        )
        try:
            return future.result(timeout=60)
        except Exception as e:
            print(f"Error getting bot response from mind: {e}")
            # The mind now handles its own performance logging.
            # self.performance_monitor.log_event('ollama_response', 'failure', {'error': str(e)})
            return {"reply": "I'm having a bit of trouble with my thoughts right now.", "style": {"length": "normal", "delivery": {"volume": "normal", "rate": "normal"}}}

    def process_bot_response(self, user_input, bot_response_data):
        """Handles the bot's response by updating history, displaying, and speaking."""
        # Handle cases where the response is a raw string (e.g., an error message)
        if isinstance(bot_response_data, dict):
            bot_response = bot_response_data.get("reply", "I seem to be at a loss for words.")
            style = bot_response_data.get("style", {})
        else:
            bot_response = str(bot_response_data)
            style = {}
        
        self.conversation_history.append({"role": "assistant", "content": bot_response})
        self.db.add_chat_log('aichris', 'AI Chris', 'assistant', bot_response)
        
        # Add to short-term memory
        self.short_term_memory.append({"user": user_input, "assistant": bot_response, "timestamp": time.time()})
        if len(self.short_term_memory) > 10:
            self.save_to_long_term_memory(self.short_term_memory.pop(0))
        
        # Update the display
        self.append_text_signal.emit(f"<b style=\"color:#50fa7b\">AI Chris:</b> {bot_response}")
        
        # Speak the response using the specified style
        self.speak(bot_response, style=style)

    def save_to_long_term_memory(self, memory_item):
        """Saves an item to the long-term memory file."""
        try:
            with open(LONG_TERM_MEMORY_FILE, 'a') as f:
                f.write(json.dumps(memory_item) + '\n')
        except Exception as e:
            print(f"Error saving to long-term memory: {e}")

    def process_speech_queue(self):
        """Process the speech queue to prevent simultaneous speaking."""
        while True:
            # .get() is a blocking call, it will wait here until an item is in the queue.
            speech_item = self.speech_queue.get()
            
            # Once we have an item, we are officially "speaking".
            # The _process_speech_item will submit the task and return immediately.
            # The callback `on_done` in that method will reset the is_speaking flag.
            # This serialized processing of the queue ensures no overlap.
            self.is_speaking = True
            
            character = speech_item["character"]
            text = speech_item["text"]
            voice = speech_item["voice"]
            avatar = speech_item["avatar"]
            style = speech_item.get("style", {}) # Get style, default to empty dict
            
            self._process_speech_item(character, text, voice, avatar, style)
    
    def _process_speech_item(self, character, text, voice, avatar, style):
        """Process a single speech item by submitting it to the async loop."""
        try:
            print(f"{character} speaking: {text[:50]}...")
            
            # This is the coroutine that will be run in the event loop
            coro = self._speak(character, text, voice, avatar, style)
            
            # Submit the coroutine to the running event loop in the other thread
            future = asyncio.run_coroutine_threadsafe(coro, self.async_loop)
            
            # Add a callback to reset the speaking flag and handle exceptions when done
            def on_done(f):
                self.is_speaking = False
                try:
                    # Retrieve result to raise any exceptions that occurred during the task
                    f.result()
                except Exception as e:
                    print(f"Error during speech playback: {e}")

            future.add_done_callback(on_done)
            
        except Exception as e:
            print(f"Error submitting speech item to async loop: {e}")
            # If submission fails, reset the flag immediately
            self.is_speaking = False

    async def _speak(self, character, text, voice, avatar, style):
        """Generates and plays speech audio. This is a coroutine."""
        try:
            # Filter out emojis, hashtags, etc. for TTS
            filtered_text = self.filter_emojis(text)
            
            # Log if filtering changed the text
            if filtered_text != text:
                print(f"Filtered text for TTS: {filtered_text[:50]}...")

            # Get voice settings from the modulation engine as a base
            voice_settings = {}
            if character == "AIChris":
                voice_settings = self.mind.voice_modulation_engine.get_voice_settings(self.mind)
            
            # Allow LLM-specified style to override rate and volume
            delivery_style = style.get("delivery", {})
            rate_str = voice_settings.get("rate", "+0%") # Default to internal state
            volume_str = voice_settings.get("volume", "+0%") # Default to internal state
            
            if delivery_style.get("rate") == "fast": rate_str = "+25%"
            elif delivery_style.get("rate") == "slow": rate_str = "-25%"
            
            if delivery_style.get("volume") == "loud": volume_str = "+25%"
            elif delivery_style.get("volume") == "whisper": volume_str = "-50%"

            # Generate speech audio asynchronously
            communicate = self.edge_tts_communicate_class(
                filtered_text, 
                voice, 
                pitch=voice_settings.get("pitch", "+0Hz"),
                rate=rate_str,
                volume=volume_str
            )
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name
            await communicate.save(temp_path)
            # The mind now handles its own performance logging
            # self.performance_monitor.log_event('tts_generation', 'success')
            
            # The rest of the playback logic is blocking (pygame, time.sleep),
            # so run it in an executor to avoid blocking the async event loop.
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._play_audio_with_animation, temp_path, character, filtered_text, avatar)

        except Exception as e:
            # The mind's generate_chat_response already logs ollama failures.
            # This will log failures for TTS generation specifically.
            self.mind.performance_monitor.log_event('tts_generation', 'failure', {'error': str(e)})
            print(f"Error in _speak coroutine: {e}")
            # Re-raise to be caught by the future's done callback
            raise
        finally:
            # Ensure the temp file is cleaned up
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def _play_audio_with_animation(self, temp_path, character, filtered_text, avatar):
        """Handles the blocking part of audio playback and mouth animation."""
        try:
            import pygame

            try:
                if os.path.getsize(temp_path) > 0:
                    audio = MP3(temp_path)
                    duration = audio.info.length
                else:
                    return
            except Exception as e:
                print(f"Error getting audio duration: {e}")
                return

            # Estimate syllables for more natural mouth movement
            syllable_count = self.estimate_syllables(filtered_text)
            if syllable_count == 0:
                syllable_count = 1
                
            # Calculate interval based on syllables
            speech_rate = 4.5 if character == "AIChris" else 5.0  # syllables per second
            interval = 1.0 / speech_rate  # seconds per syllable
            
            def animate_avatar():
                # Use faster animation cycle for more natural looking speech
                mouth_open_time = interval * (0.4 if character == "AIChris" else 0.35)
                mouth_closed_time = interval * (0.6 if character == "AIChris" else 0.65)
                
                start_time = time.time()
                end_time = start_time + duration
                
                while time.time() < end_time:
                    if not pygame.mixer.get_init() or not pygame.mixer.music.get_busy():
                        break
                    avatar.show_open()
                    time.sleep(mouth_open_time)
                    avatar.show_closed()
                    time.sleep(mouth_closed_time)
            
            # Initialize pygame mixer if needed
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            
            # Animate mouth while speaking
            animation_thread = threading.Thread(target=animate_avatar, daemon=True)
            animation_thread.start()
            avatar.show_open()
            
            # Play the audio
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            
            # Wait for audio to finish
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            # Clean up
            avatar.show_closed()

        except Exception as e:
            print(f"Error in audio playback/animation: {e}")

    def speak(self, text, voice="en-US-ChristopherNeural", style=None):
        """Add speech to the queue for AI Chris"""
        self.speech_queue.put({
            "character": "AIChris",
            "text": text,
            "voice": voice,
            "avatar": self.avatar_window,
            "style": style or {}
        })
        
    def process_command(self, command_input: str):
        """Processes a text command by routing it to the command handler."""
        cmd_parts = command_input.lower().strip().split()
        command_name = cmd_parts[0][1:]  # Remove the '/'
        args = cmd_parts[1:]

        # Find the command in the text_commands map
        command_method = self.command_handler.text_commands.get(command_name)

        if command_method:
            command_method(args)
        else:
            self.chat_display.append(f"<b style=\"color:#ff5555\">Error:</b> Unknown command: {command_name}")

    def init_tts(self):
        """Initialize Edge TTS"""
        try:
            print("Initializing TTS engine...")
            self.edge_tts_communicate_class = edge_tts.Communicate
        except Exception as e:
            print(f"Error initializing TTS engine: {e}")
            import traceback
            traceback.print_exc()
            
    def run_single_voice_interaction(self):
        """Runs a single, discrete listening/transcription/response cycle in a background thread."""
        # Disable the button to prevent multiple clicks
        self.speak_button.setEnabled(False)
        self.speak_button.setText("Listening...")
        self.speak_button.setStyleSheet("background-color: #ffb86c; color: #282a36; border: none; border-radius: 5px; padding: 5px 15px; font-size: 14px; font-weight: bold;")
        
        # Run the actual logic in a thread to keep the UI responsive
        threading.Thread(target=self._voice_interaction_worker, daemon=True).start()

    def _voice_interaction_worker(self):
        """The actual worker for the voice interaction thread."""
        # This contains the logic from the old voice_call_loop for one cycle.
        try:
            vad = webrtcvad.Vad()
            vad.set_mode(3)
        except Exception as e:
            print(f"Failed to initialize VAD: {e}.")
            self.update_status_signal.emit("Error: VAD could not start.")
            self.reset_speak_button() # Reset the button on failure
            return

        sample_rate = 16000
        frame_duration = 30
        frame_size = int(sample_rate * frame_duration / 1000)

        audio_data = self.listen_for_speech_vad(vad, frame_size, sample_rate)

        if audio_data is not None:
            # If the user spoke while the bot was talking, interrupt the bot.
            if self.is_speaking:
                print("User interrupted. Stopping TTS.")
                self.stop_tts()
                # A short wait to ensure the TTS flag is cleared
                time.sleep(0.5)

            transcription = self.transcribe_in_memory(audio_data, sample_rate)

            if transcription:
                # If a voice command was processed, the loop continues. Otherwise, process as chat.
                if not self.process_voice_command(transcription):
                    self.append_text_signal.emit(f"<b style=\"color:#bd93f9\">You (Voice):</b> {transcription}")
                    
                    # Generate and process the bot's response
                    response_data = self.get_bot_response(transcription)
                    if response_data:
                        self.process_bot_response(transcription, response_data)
        
        # Always re-enable the button when done
        self.reset_speak_button()

    def reset_speak_button(self):
        """Resets the Speak button to its default state. Must be thread-safe."""
        # This function can be called from a worker thread, so we use signals
        # or QTimer.singleShot to safely update the UI from the main thread.
        # For simplicity here, we assume direct call is safe enough for this case,
        # but a more robust solution would use signals.
        self.speak_button.setEnabled(True)
        self.speak_button.setText("Speak 🎤")
        self.speak_button.setStyleSheet("background-color: #50fa7b; color: #282a36; border: none; border-radius: 5px; padding: 5px 15px; font-size: 14px; font-weight: bold;")

    def listen_for_speech_vad(self, vad, frame_size, sample_rate):
        """
        Uses VAD to listen for speech. Starts recording when speech is detected
        and stops after a period of silence. This version is simplified for robustness.
        """
        SILENCE_LIMIT_S = 2.0  # Stop after 2 seconds of silence
        START_TIMEOUT_S = 5.0 # Give up if no speech in 5 seconds
        MAX_RECORDING_S = 20.0 # Max recording length

        frame_duration_ms = 30
        frames_per_second = 1000 / frame_duration_ms
        
        silence_frames_needed = int(SILENCE_LIMIT_S * frames_per_second)
        start_timeout_frames = int(START_TIMEOUT_S * frames_per_second)
        max_frames = int(MAX_RECORDING_S * frames_per_second)

        self.update_status_signal.emit("Listening...")

        recorded_frames = []
        has_started = False
        silent_frames = 0
        total_frames = 0

        try:
            stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16', blocksize=frame_size)
            with stream:
                while total_frames < max_frames:
                    frame, overflowed = stream.read(frame_size)
                    if overflowed:
                        print("Warning: Voice input overflowed.")
                    total_frames += 1

                    is_speech = vad.is_speech(frame.tobytes(), sample_rate)

                    if not has_started:
                        if is_speech:
                            self.update_status_signal.emit("Hearing you...")
                            has_started = True
                            recorded_frames.append(frame)
                        elif total_frames > start_timeout_frames:
                            self.update_status_signal.emit("No speech detected.")
                            return None
                    else: # We have started
                        recorded_frames.append(frame) # Record speech and silence
                        if is_speech:
                            silent_frames = 0 # Reset silence counter on speech
                        else: # Silence after starting
                            silent_frames += 1
                            if silent_frames > silence_frames_needed:
                                self.update_status_signal.emit("Got it. Thinking...")
                                break
        except Exception as e:
            print(f"Error during audio stream: {e}")
            self.update_status_signal.emit("Error with audio device.")
            return None
        finally:
            self.update_status_signal.emit("Ready")

        if not recorded_frames or not has_started:
            return None

        # Trim the trailing silence from the recording, but keep a bit
        if len(recorded_frames) > silent_frames:
             final_frames = recorded_frames[:-silent_frames]
        else:
             final_frames = recorded_frames

        return np.concatenate(final_frames, axis=0) if final_frames else None

    def transcribe_in_memory(self, audio_data: np.ndarray, sample_rate: int):
        """Transcribes audio data directly from a NumPy array without saving to disk."""
        try:
            if audio_data is None or audio_data.size == 0:
                return None
            
            # Ensure audio is a 1D array (flatten) and convert to float32
            audio_flat = audio_data.flatten()
            audio_float32 = audio_flat.astype(np.float32) / 32768.0

            # Apply noise reduction
            reduced_noise = nr.reduce_noise(y=audio_float32, sr=sample_rate)
            
            transcription = None
            if self.whisper_model:
                result = self.whisper_model.transcribe(reduced_noise, fp16=False) # Use fp16=False for CPU
                transcription = result["text"].strip()
                self.mind.performance_monitor.log_event('whisper_transcription', 'success')
            else:
                print("Whisper model not available for transcription.")
                self.mind.performance_monitor.log_event('whisper_transcription', 'failure', {'error': 'model_not_loaded'})
            
            return transcription

        except Exception as e:
            print(f"Error during in-memory transcription: {e}")
            self.mind.performance_monitor.log_event('whisper_transcription', 'failure', {'error': str(e)})
            self.update_status_signal.emit("Sorry, I had trouble transcribing that.")
            return None

    def process_voice_command(self, transcription: str):
        """
        Processes a voice command by routing it to the command handler.
        This now checks for commands that start with a certain phrase,
        allowing for arguments in voice commands.
        """
        text = transcription.lower().strip()

        # Check for an exact match first (for commands with no arguments)
        command_method = self.command_handler.voice_commands.get(text)
        if command_method:
            command_method()
            return True

        # Handle more complex voice commands with arguments, e.g., "play song ..."
        # This iterates through the text commands (like /play) to see if the voice
        # command starts with one of them.
        for command_name, method in self.command_handler.text_commands.items():
            # We use the command name as the trigger phrase
            if text.startswith(command_name):
                # The rest of the string is treated as arguments
                args_str = text[len(command_name):].strip()
                # Split arguments by space, but handle cases where there are no args
                args = args_str.split() if args_str else []
                
                self.append_text_signal.emit(f"<b style=\"color:#50fa7b\">Voice Command:</b> {command_name} {' '.join(args)}")
                
                # Run the command's method with the extracted arguments
                # We need to ensure the method is called in a way that doesn't
                # block the main thread if it's a long-running task.
                # Assuming command methods are designed to be quick or run in a thread.
                method(args)
                return True

        return False

    def filter_emojis(self, text):
        """Filter out emojis, URLs, hashtags, and other special characters for TTS using pre-compiled regex."""
        # Replace markdown-style links with just the link text
        text = self.markdown_link_pattern.sub(r'\\1', text)
        # Remove URLs
        text = self.url_pattern.sub('', text)
        # Remove hashtags
        text = self.hashtag_pattern.sub('', text)
        # Remove emojis
        text = self.emoji_pattern.sub('', text)
        # Remove any leading/trailing whitespace
        return text.strip()

    def apply_dark_theme(self):
        self.setPalette(self.palette)

    def process_message_queue(self):
        """Process any pending messages in the message queue"""
        while True:
            # .get() is a blocking call, it waits here for an item.
            message = self.message_queue.get()
            try:
                if message.get("update_chat_only", False):
                    self.chat_display.append(message["text"])
                else:
                    self.chat_display.append(message["text"])
                    if not message.get("is_user", False):
                        # Only speak non-user messages
                        self.speak(message["text"])
            except Exception as e:
                print(f"Error processing message: {e}")

    def add_message_to_queue(self, text, is_user=False, update_chat_only=False):
        """Add a message to the queue for processing"""
        self.message_queue.put({
            "text": text,
            "is_user": is_user,
            "update_chat_only": update_chat_only
        })

    def animate_mouth(self):
        """Animate the avatar's mouth based on syllable timing"""
        if self.is_speaking and self.current_text:
            # ... existing code ...
            pass

    def estimate_syllables(self, text):
        """A simple heuristic to estimate syllables for animation timing."""
        text = text.lower()
        count = 0
        vowels = "aeiouy"
        if text:
            if text[0] in vowels:
                count += 1
            for index in range(1, len(text)):
                if text[index] in vowels and text[index-1] not in vowels:
                    count += 1
            if text.endswith("e"):
                count -= 1
            if text.endswith("le") and len(text) > 2 and text[-3] not in vowels:
                count += 1
            if count == 0:
                count = 1
        return count

    def check_code_changes(self, init=False):
        """Check for changes in any .py script and restart if necessary."""
        if not hasattr(self, 'watched_files'):
            self.watched_files = {}

        python_files = [f for f in os.listdir('.') if f.endswith('.py')]

        if init:
            for filename in python_files:
                try:
                    self.watched_files[filename] = os.path.getmtime(filename)
                except OSError:
                    pass
            return

        for filename in python_files:
            try:
                current_mtime = os.path.getmtime(filename)
                if filename in self.watched_files and current_mtime > self.watched_files[filename]:
                    print(f"Code change detected in '{filename}', restarting application...")
                    
                    # Use subprocess.Popen for a more robust restart
                    # This correctly handles paths with spaces.
                    QApplication.quit()
                    subprocess.Popen([sys.executable] + sys.argv)
                    sys.exit()
                    return 

                self.watched_files[filename] = current_mtime
            except OSError:
                continue

    def init_web_server(self):
        """Initialize and run the Flask web server in a separate thread."""
        # Establish the bridge by passing this ChatBot instance to the web_server module
        web_server.set_main_chatbot_instance(self)
        
        def run_server():
            try:
                print("Starting web server...")
                web_server.run_web_server()
            except Exception as e:
                print(f"Error running web server: {e}")

        threading.Thread(target=run_server, daemon=True).start()
        print("Web server thread started.")

    def init_discord_bot(self):
        """Initialize and run the Discord bot in a separate thread."""
        # Establish the bridge by passing this ChatBot instance to the bot module
        discord_bot.setup_bridge(self)
        
        def run_bot():
            try:
                print("Starting Discord command bot...")
                discord_bot.bot.run(discord_bot.DISCORD_TOKEN)
            except Exception as e:
                print(f"Error running Discord bot: {e}")

        threading.Thread(target=run_bot, daemon=True).start()
        print("Discord bot thread started.")

    def run_migration_from_json(self):
        """One-time migration for chatbot_state.json."""
        if not os.path.exists(CHATBOT_STATE_FILE):
            return

        print("Migrating chatbot_state.json to database...")
        try:
            with open(CHATBOT_STATE_FILE, 'r') as f:
                state = json.load(f)

            history = state.get("conversation_history", [])
            summary = state.get("long_term_summary", "No history.")

            # Save summary
            self.db.save_system_state(CHATBOT_SUMMARY_KEY, {"summary": summary})

            # Save chat history
            for message in history:
                role = message.get("role")
                content = message.get("content")
                user_id = "aichris" if role == "assistant" else "local_user"
                username = "AI Chris" if role == "assistant" else "Local User"
                if role and content:
                    self.db.add_chat_log(user_id, username, role, content)
            
            print(f"Migrated {len(history)} chat messages and summary.")
            os.rename(CHATBOT_STATE_FILE, f"{CHATBOT_STATE_FILE}.migrated")
            print(f"Renamed old chatbot state file to '{CHATBOT_STATE_FILE}.migrated'.")

        except Exception as e:
            print(f"Error during chatbot state migration: {e}")

    def show_changelog(self):
        """Reads and displays the latest changelog notes in the chat window."""
        changelog_message = ""
        try:
            if os.path.exists("changelog.md"):
                with open("changelog.md", "r", encoding="utf-8") as f:
                    changelog_content = f.read()
                
                # Find the latest version's notes
                latest_version_match = re.search(r"##\s*(.*?)\s*\n([\s\S]*)", changelog_content)
                if latest_version_match:
                    version_title = latest_version_match.group(1).strip()
                    version_notes = latest_version_match.group(2).strip()
                    
                    # Stop at the next major section (next '## ' or end of file)
                    next_section_match = re.search(r"\n##\s", version_notes)
                    if next_section_match:
                        version_notes = version_notes[:next_section_match.start()]

                    # Basic markdown to HTML conversion
                    html_notes = version_notes.replace("\n", "<br>")
                    html_notes = re.sub(r"-\s+\*\*(.*?)\*\*:", r"&nbsp;&nbsp;<b>\1:</b>", html_notes)
                    html_notes = re.sub(r"-\s+", r"&nbsp;&nbsp;- ", html_notes)
                    html_notes = html_notes.replace("**", "<b>", 1).replace("**", "</b>", 1) # For headers like **Core Values:**
                    
                    changelog_message = f"Here are the latest changes for <b>{version_title}</b>:<br><i style=\"color:#bd93f9;\">{html_notes}</i>"
                else:
                    changelog_message = "I couldn't read the details of my latest update from the changelog."
            else:
                changelog_message = "I can't seem to find my changelog file."

        except Exception as e:
            print(f"Error reading changelog: {e}")
            changelog_message = "I had trouble reading my changelog file."
            
        self.chat_display.append(changelog_message)

    def update_passive_ui(self):
        """Periodically updates UI elements that don't depend on active events."""
        # Update Mood Display
        mood_desc = self.mind.mood_engine.get_mood_description()
        mood_details = f"Happiness: {self.mind.mood_engine.mood['happiness']:.2f}, Excitement: {self.mind.mood_engine.mood['excitement']:.2f}"
        self.append_mood_signal.emit(f"{mood_desc}\n({mood_details})")

        # Update Trust Display (for local user)
        trust_desc = self.mind.trust_engine.get_trust_description('local_user')
        trust_level = self.mind.trust_engine.get_trust('local_user')
        self.append_trust_signal.emit(f"{trust_desc}\n(Level: {trust_level:.2f})")

        # Update User Profile Display (for local user, as a default)
        self.update_user_profile_ui('local_user', 'Local User')

        # Update Mental Health Display
        health_status = self.mind.mental_health_engine.get_status_description()
        self.append_mental_health_signal.emit(health_status)

        # Update Goals Display
        goals_status = self.mind.goals_engine.get_active_goals_string()
        self.append_goals_signal.emit(goals_status)

        # Update Knowledge Display
        knowledge_summary = self.mind.knowledge_base.get_all_as_string()
        self.append_knowledge_signal.emit(knowledge_summary)

        # Update Evolution Display
        values = self.mind.core_values.get_all_as_string()
        traits = self.mind.psychological_engine.get_dynamic_traits_summary()
        evolution_text = f"**Core Values:**\n{values}\n\n**Dynamic Traits:**\n{traits}"
        self.append_evolution_signal.emit(evolution_text)

    def update_user_profile_ui(self, user_id: str, username: str):
        """Fetches a user's profile and updates the UI panel."""
        profile = self.mind.user_profile_engine.get_or_create_profile(user_id, username)
        summary = profile.get_summary()
        summary_html = summary.replace('\\n', '<br>')
        self.append_user_profile_signal.emit(summary_html)

    async def generate_tts_for_web(self, text: str, style: dict) -> str | None:
        """Generates TTS audio and saves it for web access, returning the web path."""
        try:
            # Filter out emojis for cleaner TTS
            filtered_text = self.filter_emojis(text)
            if not filtered_text:
                return None

            # Get voice settings from the modulation engine
            voice_settings = self.mind.voice_modulation_engine.get_voice_settings(self.mind)
            
            # Allow LLM-specified style to override
            delivery_style = style.get("delivery", {})
            rate_str = voice_settings.get("rate", "+0%")
            volume_str = voice_settings.get("volume", "+0%")
            
            if delivery_style.get("rate") == "fast": rate_str = "+25%"
            elif delivery_style.get("rate") == "slow": rate_str = "-25%"
            if delivery_style.get("volume") == "loud": volume_str = "+25%"
            elif delivery_style.get("volume") == "whisper": volume_str = "-50%"

            # Generate a unique filename
            unique_filename = f"{int(time.time())}_{random.randint(1000, 9999)}.mp3"
            save_path = os.path.join(self.web_audio_folder, unique_filename)

            communicate = self.edge_tts_communicate_class(
                filtered_text, 
                self.tts_voice, 
                pitch=voice_settings.get("pitch", "+0Hz"),
                rate=rate_str,
                volume=volume_str
            )
            await communicate.save(save_path)
            
            # Return the web-accessible path
            return f"/audio/{unique_filename}"
            
        except Exception as e:
            print(f"Error generating TTS for web: {e}")
            return None

if __name__ == '__main__':
    chosen_model = OLLAMA_MODEL
    print(f"AI Chris will use the default model: {chosen_model}\\n")

    if chosen_model:
        # Initialize the database engine once
        db_engine = DatabaseEngine()

        # Start the Qt application
        app = QApplication(sys.argv)
        window = ChatBot(model_id=chosen_model, db_engine=db_engine)
        window.show()
        sys.exit(app.exec_())
    else:
        print("No model specified in OLLAMA_MODEL. Application will not start.")
        sys.exit(1)
