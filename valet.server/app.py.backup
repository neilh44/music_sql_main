import os
from flask import Flask, request, jsonify
import pandas as pd
from dotenv import load_dotenv
from llm_service import LLMService
from ai_assistant import AIAssistant
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from flask_cors import CORS
from followup_generator import FollowUpQuestionGenerator

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
        
    def add_context(self, session_id: str, query: str, sql_query: str, results: Any, 
                   explanation: Optional[str] = None, 
                   visualization_type: Optional[str] = None,
                   visualization_data: Optional[Any] = None) -> None:
        """
        Add a new interaction to the context
        """
        if session_id not in self.conversation_contexts:
            self.conversation_contexts[session_id] = []
            
        context = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "sql_query": sql_query,
            "results": results,
            "explanation": explanation,
            "visualization": {
                "type": visualization_type,
                "data": visualization_data
            } if visualization_type else None
        }
        
        self.conversation_contexts[session_id].append(context)
        if len(self.conversation_contexts[session_id]) > self.max_history:
            self.conversation_contexts[session_id].pop(0)
    
    def get_context(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the conversation context for a session
        """
        return self.conversation_contexts.get(session_id, [])
    
    def clear_context(self, session_id: str) -> None:
        """
        Clear the context for a session
        """
        if session_id in self.conversation_contexts:
            del self.conversation_contexts[session_id]

    def analyze_context(self, session_id: str) -> Dict[str, Any]:
        """
        Analyze the context for patterns and insights
        """
        context = self.get_context(session_id)
        if not context:
            return {
                "interaction_count": 0,
                "common_topics": [],
                "query_patterns": {}
            }

        # Analyze queries
        queries = [item["query"].lower() for item in context]
        
        # Track topics and patterns
        topic_patterns = {
            "parking": ["spot", "space", "park", "lot"],
            "availability": ["available", "free", "open", "vacant"],
            "pricing": ["cost", "price", "rate", "fee"],
            "timing": ["time", "duration", "hour", "when"],
            "location": ["where", "level", "floor", "area"]
        }
        
        topic_counts = {topic: 0 for topic in topic_patterns}
        for query in queries:
            for topic, keywords in topic_patterns.items():
                if any(keyword in query for keyword in keywords):
                    topic_counts[topic] += 1

        # Identify common topics (mentioned more than once)
        common_topics = [
            topic for topic, count in topic_counts.items() 
            if count > 1
        ]

        # Analyze query complexity
        query_patterns = {
            "comparison_queries": len([q for q in queries if "compare" in q or "versus" in q or "vs" in q]),
            "trend_analysis": len([q for q in queries if "trend" in q or "pattern" in q or "over time" in q]),
            "specific_searches": len([q for q in queries if any(specific in q for specific in ["specific", "exact", "particular"])])
        }

        return {
            "interaction_count": len(context),
            "common_topics": common_topics,
            "query_patterns": query_patterns,
            "recent_focus": common_topics[-1] if common_topics else None
        }

    def get_relevant_context(self, session_id: str, current_query: str) -> List[Dict[str, Any]]:
        """
        Get context entries relevant to the current query
        """
        context = self.get_context(session_id)
        if not current_query or not context:
            return []

        # Convert current query to lowercase for comparison
        current_query_lower = current_query.lower()
        
        # Define relevance criteria
        def calculate_relevance(entry: Dict[str, Any]) -> float:
            query = entry["query"].lower()
            # Simple relevance score based on word overlap
            current_words = set(current_query_lower.split())
            entry_words = set(query.split())
            word_overlap = len(current_words.intersection(entry_words))
            return word_overlap

        # Sort context entries by relevance
        relevant_entries = sorted(
            context,
            key=calculate_relevance,
            reverse=True
        )

        # Return top 3 most relevant entries
        return relevant_entries[:3]

    def get_suggested_questions(self, session_id: str) -> List[str]:
        """
        Generate suggested questions based on context analysis
        """
        analysis = self.analyze_context(session_id)
        context = self.get_context(session_id)
        
        if not context:
            return [
                "What would you like to know about parking availability?",
                "Would you like to check parking rates?",
                "Would you like to find a specific type of parking spot?"
            ]

        suggestions = []
        
        # Add topic-based suggestions
        for topic in analysis["common_topics"]:
            if topic == "parking":
                suggestions.append("Would you like to check specific parking spot features?")
            elif topic == "availability":
                suggestions.append("Would you like to check availability at a different time?")
            elif topic == "pricing":
                suggestions.append("Would you like to compare rates between different spots?")
            elif topic == "timing":
                suggestions.append("Would you like to see peak parking hours?")
            elif topic == "location":
                suggestions.append("Would you like to explore different parking areas?")

        # Add pattern-based suggestions
        patterns = analysis["query_patterns"]
        if patterns["comparison_queries"] > 0:
            suggestions.append("Would you like to compare with other time periods?")
        if patterns["trend_analysis"] > 0:
            suggestions.append("Would you like to see any other trends?")

        # Ensure we return at least 3 suggestions
        default_suggestions = [
            "Would you like to explore parking availability?",
            "Should we look at parking rates?",
            "Would you like to see parking trends?"
        ]

        # Combine and limit suggestions
        all_suggestions = suggestions + default_suggestions
        return list(dict.fromkeys(all_suggestions[:4]))  # Remove duplicates and limit to 4
    
    
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