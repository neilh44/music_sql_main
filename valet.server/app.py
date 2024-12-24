import os
from flask import Flask, request, jsonify
import pandas as pd
from dotenv import load_dotenv
from llm_service import LLMService
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from flask_cors import CORS

# Set up Flask app
app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContextManager:
    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.conversation_contexts: Dict[str, List[Dict[str, Any]]] = {}
    
    def add_context(self, conversation_id: str, query: str, sql: str, results: Any) -> None:
        if conversation_id not in self.conversation_contexts:
            self.conversation_contexts[conversation_id] = []
            
        context = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "sql": sql,
            "results": results
        }
        
        self.conversation_contexts[conversation_id].append(context)
        if len(self.conversation_contexts[conversation_id]) > self.max_history:
            self.conversation_contexts[conversation_id].pop(0)
    
    def get_context(self, conversation_id: str) -> List[Dict[str, Any]]:
        return self.conversation_contexts.get(conversation_id, [])
    
    def clear_context(self, conversation_id: str) -> None:
        if conversation_id in self.conversation_contexts:
            del self.conversation_contexts[conversation_id]

def generate_default_followup_questions(user_input: str, results: list) -> List[str]:
    if not results:
        return [
            "Can you rephrase your query?",
            "Would you like to try a different search?",
            "Do you want to broaden the search criteria?"
        ]
    
    return [
        "Can you provide more details about these results?",
        "What insights can we draw from these results?",
        "Are there any specific trends you'd like to explore?"
    ]

# Load environment variables
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
db_path = os.getenv("DB_PATH")

# Initialize services
try:
    llm_service = LLMService(api_key=api_key, db_path=db_path)
    ai_assistant = AIAssistant(api_key=api_key)
    context_manager = ContextManager()
except Exception as e:
    logger.error(f"Error initializing services: {str(e)}")
    raise e

@app.route("/")
def index():
    return jsonify({
        "message": "Valet Server API",
        "status": "running",
        "endpoints": {
            "/query": "POST - Process natural language queries",
            "/clear-context": "POST - Clear conversation context"
        }
    })

@app.route("/query", methods=["POST"])
def process_query():
    try:
        data = request.json
        if not data or 'query' not in data:
            return jsonify({
                "success": False,
                "error": "No query provided"
            }), 400

        user_input = data['query'].strip()
        conversation_id = data.get('conversation_id', 'default')

        # Get conversation context
        conversation_context = context_manager.get_context(conversation_id)

        # Process with AI Assistant
        assistant_response = ai_assistant.process_query(
            user_input,
            context=conversation_context
        )
        
        if not assistant_response["success"]:
            return jsonify({
                "success": False,
                "error": assistant_response["error"]
            }), 400

        # Convert to SQL with context
        sql_result = llm_service.convert_to_sql_query(
            user_input,
            context=conversation_context
        )
        
        if not sql_result["success"]:
            return jsonify({
                "success": False,
                "error": f"SQL Conversion Error: {sql_result['error']}"
            }), 400

        # Execute query
        query_result = llm_service.execute_query(sql_result["query"])
        
        if not query_result["success"]:
            return jsonify({
                "success": False,
                "error": f"Query Execution Error: {query_result['error']}"
            }), 400

        # Store the interaction in context
        context_manager.add_context(
            conversation_id,
            user_input,
            sql_result["query"],
            query_result["results"]
        )

        # Generate follow-up questions
        followup_questions = generate_default_followup_questions(user_input, query_result["results"])

        response = {
            "success": True,
            "sql_query": sql_result["query"],
            "query_results": query_result["results"],
            "columns": query_result["columns"],
            "explanation": assistant_response.get("explanation", "Results processed successfully."),
            "context_used": bool(conversation_context and sql_result.get("context_used")),
            "followup_questions": followup_questions
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Error processing query: {str(e)}"
        }), 500

@app.route("/clear-context", methods=["POST"])
def clear_context():
    try:
        data = request.json
        conversation_id = data.get('conversation_id', 'default')
        context_manager.clear_context(conversation_id)
        return jsonify({
            "success": True,
            "message": "Context cleared successfully"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error clearing context: {str(e)}"
        }), 500

if __name__ == "__main__":
    app.run(debug=True)