import time

class ConversationManager:
    def __init__(self, bot_id, partner_bot_id, max_turns=6, timeout=60):
        self.bot_id = bot_id
        self.partner_bot_id = partner_bot_id
        self.max_turns = max_turns
        self.timeout = timeout
        self.reset()

    def reset(self):
        self.turns = 0
        self.last_speaker = None
        self.last_timestamp = time.time()
        self.history = []

    def should_respond(self, message):
        now = time.time()
        if now - self.last_timestamp > self.timeout:
            self.reset()

        if message.author.id == self.bot_id:
            return False  # Ignore own messages

        if self.turns >= self.max_turns:
            return False  # Conversation maxed out

        if message.author.id == self.partner_bot_id or not message.author.bot:
            return True

        return False

    def register_turn(self, message):
        self.last_speaker = message.author.id
        self.last_timestamp = time.time()
        self.turns += 1
        self.history.append((message.author.name, message.content))
