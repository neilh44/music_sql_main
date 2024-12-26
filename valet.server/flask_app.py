from flask import Flask, request, jsonify
import logging
import uuid
import os
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from flask_cors import CORS
from nl_converter import NLConverter  # Ensure you have this import
from followup_generator import FollowUpQuestionGenerator
import json 


# Import your custom classes
from context_manager import ContextManager
from llm_service import LLMService
from nl_converter import NLConverter  

# Set up Flask app
app = Flask(__name__)

# Configure CORS with specific options
CORS(app, resources={
    r"/*": {
        "origins": ["*"],  # Allow all origins
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Origin"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "send_wildcard": False
    }
})

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# Handle OPTIONS requests explicitly
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return jsonify({}), 200


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get configuration from environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DB_PATH = os.getenv("DB_PATH", "./data/sqlite.db")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "5"))

# Initialize services
try:
    # Initialize context manager
    context_manager = ContextManager(max_history=MAX_HISTORY)
    
    # Initialize LLM service with required parameters
    llm_service = LLMService(
        api_key=GROQ_API_KEY,
        db_path=DB_PATH
    )
    
    # Initialize NLConverter with the required api_key
    nl_converter = NLConverter(api_key=GROQ_API_KEY)  # Fixed: Added api_key parameter

    logger.info("Services initialized successfully")
    
except Exception as e:
    logger.error(f"Error initializing services: {str(e)}")
    raise
    
    # Initialize services globally
    data_analyzer = ParkingDataAnalyzer()
    question_generator = LLMQuestionGenerator(api_key=GROQ_API_KEY)
    context_manager = ContextManager()

def process_query_results(query_result: dict, natural_query: str, conversation_context: list) -> dict:
    """
    Process query results and generate natural language explanation
    
    Args:
        query_result: Dictionary containing query execution results
        natural_query: Original natural language query
        conversation_context: List of previous conversation interactions
        
    Returns:
        Dictionary containing processed results and metadata
    """
    try:
        if not query_result.get("success"):
            return {
                "success": False,
                "error": query_result.get("error", "Unknown error processing query results")
            }

        # Extract results and columns
        results = query_result.get("results", [])
        columns = query_result.get("columns", [])

        # Analyze result type and structure
        result_type = "empty" if not results else "single" if len(results) == 1 else "multiple"
        
        # Generate context-aware explanation
        if result_type == "empty":
            explanation = "I didn't understand the question. Could you please try asking again."
        else:
            # Use NLConverter for natural language explanation
            nl_response = nl_converter.convert_to_natural_language(
                query_result={
                    "success": True,
                    "results": results,
                    "columns": columns
                },
                original_query=natural_query,
                context=conversation_context
            )
            
            if not nl_response["success"]:
                logger.error(f"NL conversion failed: {nl_response.get('error')}")
                explanation = "Sorry, I couldn't generate a proper explanation for the results."
            else:
                explanation = nl_response["explanation"]

        return {
            "success": True,
            "results": results,
            "columns": columns,
            "explanation": explanation,
            "context_used": bool(conversation_context)
        }

    except Exception as e:
        logger.error(f"Error processing results: {str(e)}")
        return {
            "success": False,
            "error": f"Error processing results: {str(e)}"
        }

# Validate required environment variables
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY not found in environment variables")
    raise ValueError("GROQ_API_KEY environment variable is required")

# Initialize services
try:
    # Initialize context manager
    context_manager = ContextManager(max_history=MAX_HISTORY)
    
    # Initialize LLM service with required parameters
    llm_service = LLMService(
        api_key=GROQ_API_KEY,
        db_path=DB_PATH
    )
    
    logger.info("Services initialized successfully")
    
except Exception as e:
    logger.error(f"Error initializing services: {str(e)}")
    raise



@app.route("/query", methods=["POST"])
def process_query():
    """
    Process natural language query endpoint
    
    Expected JSON body:
    {
        "query": "natural language query string",
        "session_id": "optional session identifier"
    }
    """
    try:
        request_data = request.get_json()
        
        if not request_data or "query" not in request_data:
            return jsonify({
                "success": False,
                "error": "Missing required 'query' field"
            }), 400

        natural_query = request_data["query"].strip()
        session_id = request_data.get("session_id", str(uuid.uuid4()))

        if not natural_query:
            return jsonify({
                "success": False,
                "error": "Empty query provided"
            }), 400

        # Get conversation context
        conversation_context = context_manager.get_context(session_id)

        # Convert to SQL
        sql_result = llm_service.convert_to_sql_query(
            natural_query,
            context=conversation_context
        )

        if not sql_result["success"]:
            return jsonify({
                "success": False,
                "error": f"SQL conversion failed: {sql_result['error']}"
            }), 

        # Execute query
        query_result = llm_service.execute_query(sql_result["query"])

        if not query_result["success"]:
            return jsonify({
                "success": False,
                "error": f"Query execution failed: {query_result['error']}"
            }), 500

        # Process results and generate explanation
        processed_result = process_query_results(
            query_result,
            natural_query,
            conversation_context
        )

        if not processed_result["success"]:
            return jsonify({
                "success": False,
                "error": processed_result["error"]
            }), 500

        # Determine visualization type based on query and results
        visualization_type = None
        visualization_data = None
        
        if "trend" in natural_query.lower():
            visualization_type = "line"
        elif "compare" in natural_query.lower():
            visualization_type = "bar"
        elif "distribution" in natural_query.lower():
            visualization_type = "pie"

        # Add to context
        context_manager.add_context(
            session_id=session_id,
            query=natural_query,
            sql_query=sql_result["query"],
            results=query_result["results"],
            explanation=processed_result["explanation"],
            visualization_type=visualization_type,
            visualization_data=visualization_data
        )

        # Analyze context for patterns
        context_analysis = context_manager.analyze_context(session_id)

        # Return successful response with SQL response included
        return jsonify({
            "success": True,
            "session_id": session_id,
            "sql_query": sql_result["query"],  # Include the SQL query
            "results": query_result["results"],  # Include the SQL results
            "columns": processed_result["columns"],
            "explanation": processed_result["explanation"],
            "context_used": processed_result["context_used"],
            "context_analysis": context_analysis,
            "visualization": {
                "type": visualization_type,
                "data": visualization_data
            } if visualization_type else None
        })

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500

@app.route("/context", methods=["GET"])
def get_context():
    """Get conversation context for a session"""
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({
            "success": False,
            "error": "Missing session_id parameter"
        }), 400

    context = context_manager.get_context(session_id)
    return jsonify({
        "success": True,
        "session_id": session_id,
        "context": context
    })

@app.route("/context", methods=["DELETE"])
def clear_context():
    """Clear conversation context for a session"""
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({
            "success": False,
            "error": "Missing session_id parameter"
        }), 400

    context_manager.clear_context(session_id)
    return jsonify({
        "success": True,
        "message": "Context cleared successfully",
        "session_id": session_id
    })

@app.route("/followup", methods=["POST"])
def get_followup_questions():
    """Generate follow-up questions using LLM based on session context and current query"""
    try:
        request_data = request.get_json()
        
        if not request_data or "session_id" not in request_data:
            return jsonify({
                "success": False,
                "error": "Missing required 'session_id' field"
            }), 400

        session_id = request_data["session_id"]
        current_query = request_data.get("query", "")

        # Get conversation context
        conversation_context = context_manager.get_context(session_id)
        
        # Get the most recent results from context
        latest_interaction = conversation_context[-1] if conversation_context else {}
        results = latest_interaction.get("results", [])

        # Generate follow-up questions using the generator
        followup_generator = FollowUpQuestionGenerator(api_key=GROQ_API_KEY, db_path=DB_PATH)
        
        # Prepare prompt and context
        prompt = followup_generator.prepare_llm_prompt(
            current_query=current_query,
            conversation_context=conversation_context,
            results=results
        )

        # Call LLM synchronously
        completion = followup_generator.client.chat.completions.create(
            model="llama3-8b-8192",  # Using a specific model
            messages=[
                {
                    "role": "system",
                    "content": """You are a helpful assistant generating follow-up questions for a parking management system. 
                    Always respond with a JSON array of exactly 4 questions that are relevant to the current query and context.
                    Focus on exploring different aspects of the query subject and suggesting related analyses."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=300
        )

        # Get response content
        response_content = completion.choices[0].message.content
        
        # Log the raw response for debugging
        followup_generator.logger.info(f"LLM Raw Response: {response_content}")

        try:
            questions = json.loads(response_content)
            
            # Validate and clean questions
            if not isinstance(questions, list):
                followup_generator.logger.error(f"LLM response is not a list: {response_content}")
                questions = followup_generator._get_fallback_questions()
            else:
                questions = [
                    str(q).strip() 
                    for q in questions 
                    if isinstance(q, (str, int, float))
                ]
                
                # Ensure exactly 4 questions
                while len(questions) < 4:
                    questions.append(followup_generator._get_fallback_question())
                questions = questions[:4]
            
        except json.JSONDecodeError as e:
            followup_generator.logger.error(f"Failed to parse LLM response as JSON: {str(e)}\nResponse: {response_content}")
            questions = followup_generator._get_fallback_questions()

        return jsonify({
            "success": True,
            "session_id": session_id,
            "followup_questions": questions,
            "context_used": bool(conversation_context),
            "debug_info": {
                "raw_llm_response": response_content,
                "prompt_used": prompt
            }
        })

    except Exception as e:
        logger.error(f"Error generating follow-up questions: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}",
            "debug_info": {
                "error_type": type(e).__name__,
                "error_details": str(e)
            }
        }), 500


@app.route("/context/export", methods=["GET"])
def export_context():
    """Export conversation context for a session"""
    session_id = request.args.get("session_id")
    format_type = request.args.get("format", "json").lower()

    if not session_id:
        return jsonify({
            "success": False,
            "error": "Missing session_id parameter"
        }), 400

    try:
        exported_context = context_manager.export_context(session_id, format=format_type)
        return jsonify({
            "success": True,
            "session_id": session_id,
            "format": format_type,
            "data": exported_context
        })
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400

if __name__ == "__main__":
    app.run(debug=True)