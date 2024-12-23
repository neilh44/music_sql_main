import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY")
        self.db_path = os.getenv("DB_PATH")
        
    def validate(self):
        if not self.api_key or not self.db_path:
            raise ValueError("Missing API key or database path in environment variables.")
