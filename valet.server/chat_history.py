import json
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class ChatHistory:
    def __init__(self):
        self.messages = []
        self.load_from_disk()
    
    def add_message(self, role, content, sql_query=None, results=None):
        message = {
            'id': str(uuid.uuid4()),
            'role': role,
            'content': content,
            'sql_query': sql_query,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
        self.messages.append(message)
        self.save_to_disk()
        return message['id']
    
    def get_message_by_id(self, message_id):
        return next((msg for msg in self.messages if msg['id'] == message_id), None)
    
    def get_conversation_pair(self, message_id):
        message = self.get_message_by_id(message_id)
        if message:
            idx = self.messages.index(message)
            if idx + 1 < len(self.messages):
                return [message, self.messages[idx + 1]]
            return [message]
        return []
    
    def search_messages(self, query):
        return [msg for msg in self.messages 
                if query.lower() in msg['content'].lower()]
    
    def save_to_disk(self):
        try:
            with open('chat_history.json', 'w') as f:
                json.dump(self.messages, f)
        except Exception as e:
            logger.error(f"Error saving chat history: {e}")
    
    def load_from_disk(self):
        try:
            with open('chat_history.json', 'r') as f:
                self.messages = json.load(f)
        except FileNotFoundError:
            self.messages = []
        except Exception as e:
            logger.error(f"Error loading chat history: {e}")
            self.messages = []

    def export_conversation(self, message_id):
        conversation = self.get_conversation_pair(message_id)
        if conversation:
            return {
                'timestamp': conversation[0]['timestamp'],
                'query': conversation[0]['content'],
                'response': conversation[1] if len(conversation) > 1 else None
            }
        return None