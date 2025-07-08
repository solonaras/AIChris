document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    // --- User Identification ---
    let userId = localStorage.getItem('aiChrisUserId');
    if (!userId) {
        // Generate a simple but effective unique ID
        userId = `web-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        localStorage.setItem('aiChrisUserId', userId);
    }
    console.log(`User identified with ID: ${userId}`);
    // --- End User Identification ---

    const messagesContainer = document.getElementById('chat-messages');
    const input = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const statusIndicator = document.getElementById('status-indicator');
    const avatarImg = document.getElementById('avatar-img');

    const avatar_closed_src = "chris avatar cropped.png";
    const avatar_open_src = "Aichrisopenmouth.png";
    let isSpeaking = false;
    let animationFrameId;

    const addMessage = (author, text, type) => {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${type}-message`);

        // Sanitize text to prevent HTML injection
        const sanitizedText = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");

        if (type === 'bot') {
            messageElement.innerHTML = `<strong>${author}:</strong> ${sanitizedText}`;
        } else {
            messageElement.textContent = sanitizedText;
        }
        
        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    };

    const sendMessage = () => {
        const messageText = input.value.trim();
        if (messageText) {
            addMessage('You', messageText, 'user');
            socket.emit('user_message', { message: messageText, userId: userId });
            input.value = '';
        }
    };

    sendButton.addEventListener('click', sendMessage);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    const animateMouth = () => {
        if (!isSpeaking) {
            avatarImg.src = avatar_closed_src;
            cancelAnimationFrame(animationFrameId);
            return;
        }
        // Simple toggle between open and closed mouth
        avatarImg.src = (avatarImg.src.includes(avatar_closed_src)) ? avatar_open_src : avatar_closed_src;
        animationFrameId = setTimeout(animateMouth, 200); // Adjust timing for natural look
    };

    socket.on('connect', () => {
        console.log('Connected to the server!');
        statusIndicator.classList.add('connected');
        addMessage('System', 'Connected to AI Chris.', 'bot');
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from the server.');
        statusIndicator.classList.remove('connected');
        addMessage('System', 'Connection lost. Attempting to reconnect...', 'bot');
    });

    socket.on('bot_response', (data) => {
        addMessage('AI Chris', data.reply, 'bot');
        if (data.audioUrl) {
            const audio = new Audio(data.audioUrl);
            audio.play();
            isSpeaking = true;
            animateMouth();

            audio.onended = () => {
                isSpeaking = false;
                avatarImg.src = avatar_closed_src; // Ensure mouth is closed
            };
        }
    });

    socket.on('connect_error', (err) => {
        console.error('Connection Error:', err);
        addMessage('System', 'Failed to connect. Please check the server.', 'bot');
    });
}); 