from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from dotenv import load_dotenv
from valet.server.llm_service import LLMService  # Changed to absolute import
from valet.server.nl_converter import NLConverter  # Changed to absolute import
from valet.server.context_manager import ContextManager  # Changed to absolute import
import logging

# Add the valet directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize services
try:
    api_key = os.getenv("GROQ_API_KEY")
    db_path = os.path.join(os.path.dirname(__file__), "../data/sqlite.db")
    
    context_manager = ContextManager(max_history=5)
    llm_service = LLMService(api_key=api_key, db_path=db_path)
    nl_converter = NLConverter(api_key=api_key)
except Exception as e:
    logger.error(f"Error initializing services: {str(e)}")
    raise e

@app.route("/api/query", methods=["POST"])
def process_query():
    try:
        logger.info("Received query request")
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({"success": False, "error": "No query provided"}), 400
            
        natural_query = data["query"].strip()
        session_id = data.get("session_id", "default")
        
        logger.info(f"Processing query: {natural_query} for session: {session_id}")
        
        # Get conversation context
        conversation_context = context_manager.get_context(session_id)
        
        # Process query with context
        sql_result = llm_service.convert_to_sql_query(natural_query, context=conversation_context)
        if not sql_result["success"]:
            return jsonify(sql_result), 500
            
        # Execute query
        query_result = llm_service.execute_query(sql_result["query"])
        if not query_result["success"]:
            return jsonify(query_result), 500
            
        # Get natural language explanation
        nl_result = nl_converter.convert_to_natural_language(
            query_result,
            natural_query,
            context=conversation_context
        )
        
        # Store context
        context_manager.add_context(
            session_id=session_id,
            query=natural_query,
            sql_query=sql_result["query"],
            results=query_result["results"],
            explanation=nl_result["explanation"]
        )
        
        response_data = {
            "success": True,
            "session_id": session_id,
            "query_results": query_result["results"],
            "columns": query_result["columns"],
            "nl_explanation": nl_result["explanation"],
            "context_used": bool(conversation_context)
        }
        
        logger.info(f"Successfully processed query. Response: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@app.route("/api/clear-context", methods=["POST"])
def clear_context():
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({"success": False, "error": "No session ID provided"}), 400
            
        context_manager.clear_context(session_id)
        return jsonify({"success": True, "message": "Context cleared successfully"})
        
    except Exception as e:
        logger.error(f"Error clearing context: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# Add health check endpoint
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200

# Default route for testing
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Valet Server API is running"}), 200

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)