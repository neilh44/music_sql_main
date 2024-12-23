import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

class NLConverter:
    def __init__(self, api_key: str):
        """Initialize NLConverter with API key and configuration."""
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger(__name__)
        
    def _format_result_data(self, results: List[Any], columns: List[str]) -> str:
        """Format query results into a readable string representation."""
        if not results or not columns:
            return "No data available"
            
        # Handle single value results (e.g., COUNT queries)
        if len(results) == 1 and len(results[0]) == 1:
            return str(results[0][0])
            
        # Format multi-column results
        formatted_rows = []
        for row in results:
            row_dict = dict(zip(columns, row))
            formatted_rows.append(str(row_dict))
            
        return "\n".join(formatted_rows)

    def _analyze_query_type(self, query: str) -> Dict[str, Any]:
        """Analyze the query to determine its characteristics."""
        query_lower = query.lower()
        
        # Query type analysis
        analysis = {
            "is_count": any(word in query_lower for word in ["count", "how many", "number of"]),
            "is_aggregate": any(word in query_lower for word in ["average", "sum", "total", "min", "max"]),
            "is_comparison": any(word in query_lower for word in ["compare", "difference", "versus", "vs"]),
            "is_trend": any(word in query_lower for word in ["trend", "over time", "pattern"]),
            "time_related": any(word in query_lower for word in ["today", "yesterday", "last week", "this month"])
        }
        
        return analysis

    def convert_to_natural_language(
        self, 
        query_result: Dict[str, Any], 
        original_query: str,
        context: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Convert query results to natural language explanation."""
        if not query_result.get("success"):
            self.logger.error("Query execution failed; no results to process.")
            return {"success": False, "error": "No results to process"}

        try:
            # Analyze query characteristics
            query_analysis = self._analyze_query_type(original_query)
            
            # Format the data
            formatted_text = self._format_result_data(
                query_result.get("results", []),
                query_result.get("columns", [])
            )

            # Build dynamic system prompt based on query type
            system_prompt = (
                "You are an intelligent data interpreter that provides clear, natural language explanations. "
                "Focus on directly answering the user's question with relevant insights from the data. "
                "Keep responses concise and professional, typically 1-3 sentences. "
                "\nGuidelines:\n"
                "- Avoid phrases like 'the data shows' or 'based on the results'\n"
                "- Start responses with the key information the user asked for\n"
                "- Include specific numbers and metrics when present\n"
                "- For trends or patterns, highlight significant changes\n"
                "- With comparisons, emphasize key differences\n"
                "- For time-based queries, mention the relevant time period"
            )

            # Construct context-aware user prompt
            user_prompt = f"""
            Question: {original_query}
            Data: {formatted_text}
            Query Type: {', '.join(k for k, v in query_analysis.items() if v)}
            Previous Context: {str(context) if context else 'None'}
            
            Generate a clear, direct explanation that answers the user's question.
            """

            # Make API request
            payload = {
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.1
            }

            response = requests.post(
                self.api_url, 
                headers=self.headers, 
                json=payload, 
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if 'choices' in result and result['choices']:
                explanation = result['choices'][0]['message']['content'].strip()
                self.logger.info(f"Generated explanation: {explanation}")
                
                return {
                    "success": True,
                    "explanation": explanation,
                    "metadata": {
                        "query_type": query_analysis,
                        "timestamp": datetime.now().isoformat(),
                        "context_used": bool(context)
                    }
                }
            
            return {
                "success": False, 
                "error": "Failed to generate explanation"
            }

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request error: {str(e)}")
            return {
                "success": False,
                "error": f"API request failed: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return {
                "success": False,
                "error": f"Error processing results: {str(e)}"
            }