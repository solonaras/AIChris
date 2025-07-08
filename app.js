// app.js - WebSocket Bridge for Twitch Chat
const tmi = require('tmi.js');
const WebSocket = require('ws');

// --- Configuration ---
// WARNING: Hardcoding credentials is a security risk. Do not share this file.
const TWITCH_USERNAME = process.env.TWITCH_USERNAME || "solonaras2";
const TWITCH_PASSWORD = process.env.TWITCH_PASSWORD; // IMPORTANT: Use a dedicated bot account token
const TWITCH_CHANNEL = process.env.TWITCH_CHANNEL || "solonaras";

// --- WebSocket Server (for Python) ---
const wss = new WebSocket.Server({ port: 8080 });
let pythonClient = null;

wss.on('connection', function connection(ws) {
    console.log("Python client connected to WebSocket server.");
    pythonClient = ws;

    ws.on('message', function incoming(message) {
        try {
            console.log(`Received message from Python: ${message}`);
            const data = JSON.parse(message);
            const { destination, content } = data;

            if (destination === 'twitch' && twitchClient && content) {
                twitchClient.say(TWITCH_CHANNEL, content);
                console.log(`Sent to Twitch: ${content}`);
            }
        } catch (e) {
            console.error('Error processing message from Python:', e);
        }
    });

    ws.on('close', () => {
        console.log("Python client disconnected.");
        pythonClient = null;
    });
});

console.log('WebSocket server started on port 8080.');

// --- Twitch Client ---
let twitchClient = null;
if (TWITCH_USERNAME && TWITCH_PASSWORD && TWITCH_CHANNEL) {
    twitchClient = new tmi.Client({
        options: { debug: true },
        identity: {
            username: TWITCH_USERNAME,
            password: TWITCH_PASSWORD
        },
        channels: [TWITCH_CHANNEL]
    });

    twitchClient.connect().catch(console.error);

    twitchClient.on('connected', () => {
        console.log(`Twitch client connected and listening to #${TWITCH_CHANNEL}`);
    });

    twitchClient.on('message', (channel, tags, message, self) => {
        if (self) return;
        console.log(`Received Twitch message from ${tags['display-name']}: ${message}`);
        if (pythonClient) {
            const data = {
                type: 'twitch_message',
                author: tags['display-name'],
                content: message
            };
            console.log(`Sending to Python: ${JSON.stringify(data)}`);
            pythonClient.send(JSON.stringify(data));
        } else {
            console.warn("Python client not connected, can't forward message");
        }
    });
} else {
    console.warn("Twitch credentials not found. Twitch bot will be disabled.");
}

console.log('Node.js bridge is running...');