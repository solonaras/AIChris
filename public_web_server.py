import os
from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit
from aichris_mind import Mind
import threading

# Initialize Flask app and SocketIO
app = Flask(__name__, static_folder='web_ui', template_folder='web_ui')
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize the Mind (no private tokens)
mind = Mind(model_id=os.getenv("OLLAMA_MODEL", "dolphin-mistral:latest"))

# In-memory conversation history per session (simple, not persistent)
user_histories = {}

@app.route('/')
def index():
    """Serve the main chat widget page (desktop by default)."""
    user_agent = request.headers.get('User-Agent', '').lower()
    if 'iphone' in user_agent or 'ipad' in user_agent or 'ipod' in user_agent:
        return render_template('index_iphone.html')
    elif 'mobile' in user_agent or 'android' in user_agent:
        return render_template('index_mobile.html')
    else:
        return render_template('index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (JS, CSS, images, etc.)."""
    return send_from_directory(app.static_folder, filename)

@socketio.on('user_message')
def handle_user_message(data):
    user_id = request.sid  # Use session ID for isolation
    user_input = data.get('message', '')
    if not user_input:
        emit('bot_message', {'message': "Please enter a message."})
        return
    # Get or create conversation history
    history = user_histories.setdefault(user_id, [])
    # Generate response (sync wrapper)
    response = mind.generate_chat_response_sync(
        user_id=user_id,
        username="Web User",
        user_input=user_input,
        conversation_history=history
    )
    # Update history
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": response['reply']})
    # Emit bot reply
    emit('bot_message', {'message': response['reply']})

if __name__ == '__main__':
    print("Starting public AI Chris web server on http://0.0.0.0:5000 ...")
    socketio.run(app, host='0.0.0.0', port=5000) 