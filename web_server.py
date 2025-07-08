from flask import Flask, render_template, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit
import os
import asyncio

# This will be the bridge to the main ChatBot instance
main_chatbot_instance = None

app = Flask(__name__, template_folder='web_ui', static_folder='web_ui')
socketio = SocketIO(app, cors_allowed_origins="*")

def set_main_chatbot_instance(instance):
    """Establishes the connection to the main ChatBot application."""
    global main_chatbot_instance
    main_chatbot_instance = instance
    print("Web server bridge established.")

@app.route('/')
def index():
    """Serves the main chat widget page, with mobile/desktop detection."""
    user_agent = request.headers.get('User-Agent', '').lower()
    if 'iphone' in user_agent or 'ipad' in user_agent or 'ipod' in user_agent:
        return render_template('index_iphone.html')
    elif 'mobile' in user_agent or 'android' in user_agent:
        return render_template('index_mobile.html')
    else:
        return render_template('index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serves static files like CSS and JS."""
    # Add a special route for the audio files
    if filename.startswith('audio/'):
        return send_from_directory(os.path.join(app.static_folder, 'audio'), filename.split('/')[1])
    return send_from_directory(app.static_folder, filename)

@app.route('/api/chat', methods=['POST'])
def handle_chat_api():
    """Handles POST requests for chat, compatible with Vercel AI Playground."""
    data = request.json
    user_input = data.get('message')
    # history = data.get('history') # Vercel may send history, we can use it later if needed.

    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    if main_chatbot_instance:
        try:
            # Use the synchronous wrapper to call the async mind function from a sync context
            response_data = main_chatbot_instance.mind.generate_chat_response_sync(
                'api_user', 
                'API User', 
                user_input, 
                [] # Start with empty history for API calls for now
            )
            
            if response_data and "reply" in response_data:
                bot_response = response_data.get("reply", "I'm at a loss for words.")
                # The template expects a JSON object with a specific structure
                return jsonify({"response": bot_response})
            else:
                return jsonify({"error": "AI failed to generate a response"}), 500
        except Exception as e:
            print(f"Error during API chat handle: {e}")
            return jsonify({"error": "An internal error occurred."}), 500
    else:
        return jsonify({"error": "AI mind is not connected"}), 503

@socketio.on('connect')
def handle_connect():
    """Handles a new client connection."""
    print('Client connected to web widget.')
    emit('bot_response', {'reply': 'Welcome! How can I help you today?'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handles a client disconnection."""
    print('Client disconnected from web widget.')

@socketio.on('user_message')
def handle_user_message(data):
    """Handles incoming messages from a user."""
    user_input = data.get('message')
    user_id = data.get('userId', f"web_guest_{request.sid}") # Use session ID as fallback
    if not user_input:
        return

    print(f"Received web message from {user_id}: {user_input}")

    if main_chatbot_instance:
        # Load the specific conversation history for this web user
        history = main_chatbot_instance.db.load_chat_history(channel=user_id)

        # Generate response using the main mind's async function, but run it
        # in the main application's event loop.
        if hasattr(main_chatbot_instance, 'async_loop') and main_chatbot_instance.async_loop.is_running():
            # First, get the text response
            text_future = asyncio.run_coroutine_threadsafe(
                main_chatbot_instance.mind.generate_chat_response(
                    user_id, 
                    'Web User', 
                    user_input, 
                    history # Pass the user's specific history
                ),
                main_chatbot_instance.async_loop
            )

            # Define a callback to handle the text response and then generate audio
            def handle_text_and_generate_audio(f):
                try:
                    response_data = f.result()
                    if not response_data or "reply" not in response_data:
                        socketio.emit('bot_response', {'reply': "Sorry, I had a problem thinking of a response."})
                        return

                    bot_response = response_data.get("reply")
                    style = response_data.get("style", {})

                    # Now, generate the TTS audio for this response
                    audio_future = asyncio.run_coroutine_threadsafe(
                        main_chatbot_instance.generate_tts_for_web(bot_response, style),
                        main_chatbot_instance.async_loop
                    )
                    audio_future.add_done_callback(
                        lambda af: emit_final_response(af, bot_response)
                    )

                except Exception as e:
                    print(f"Error in web server text generation stage: {e}")
            
            def emit_final_response(audio_future, text_response):
                audio_url = None
                try:
                    audio_url = audio_future.result()
                except Exception as e:
                    print(f"Error in web server audio generation stage: {e}")
                
                print(f"Sending web response: {text_response} with audio {audio_url}")
                socketio.emit('bot_response', {'reply': text_response, 'audioUrl': audio_url})

            text_future.add_done_callback(handle_text_and_generate_audio)
        else:
            emit('bot_response', {'reply': 'The AI mind is not fully connected. Please try again later.'})
    else:
        emit('bot_response', {'reply': 'The AI mind is not connected. Please try again later.'})

def run_web_server():
    """Runs the Flask-SocketIO web server."""
    print("Starting web server on http://0.0.0.0:5000 (all interfaces)")
    socketio.run(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    # This part is for testing the web server independently.
    print("Running web_server.py in standalone mode for testing.")
    run_web_server() 