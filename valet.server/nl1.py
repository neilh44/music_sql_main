import logging
import requests
import json
from typing import Dict, Any, List

class NLConverter:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def convert_to_natural_language(self, query_result: Dict[str, Any], original_query: str) -> Dict[str, Any]:
        """Convert query results to natural language using LLaMA-3"""
        if not query_result["success"]:
            self.logger.error("Query execution failed; no results to process.")
            return {"success": False, "error": "No results to process"}

        # Format the query result data
        formatted_data = [dict(zip(query_result["columns"], row)) for row in query_result["results"]]
        formatted_text = "\n".join([str(row) for row in formatted_data])

        # Get context analysis if available
        context_analysis = query_result.get("context_analysis", {})
        topic_focus = context_analysis.get("topic_focus", [])
        patterns = context_analysis.get("patterns", [])
        has_visualizations = context_analysis.get("has_visualizations", False)
        interaction_count = context_analysis.get("interaction_count", 0)
            
        # Prepare system and user prompts
        system_prompt = (
            "You are a data interpreter that creates clear, natural language explanations. "
            "Your job is to analyze the data, summarize key insights, and answer the original question considering the context."
            "if context is not present or other context, consider the latest query for asnwering the user prompt"
            "avoid starting the response with reference to the dataset"
            "Always provide clear, concise, and direct answers to user queries. "
            "Keep responses brief and professional, using no more than 2-3 sentences. "
            "Example:\n"
            "- Query: 'Show tickets for location X.'\n"
            "  Response: 'We didn't find a response to your query.'\n"
            "- Query: 'List sales for October.'\n"
            "  Response: 'Sales for October total $15,000 with 120 orders.'"
            "  Query; Show me count of red color car"
            "  Response: 'There are 60 red color cars'"
        )

        user_prompt = f"""
        Original question: {original_query}
        Data Summary:      {formatted_text}
        Generate a natural language explanation of the query results, considering the context & user query.
        """

        try:
            payload = {
                "model": "llama3-8b-8192",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.1
            }

            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'choices' in result and result['choices']:
                explanation = result['choices'][0]['message']['content'].strip()
                self.logger.info(f"Generated natural language explanation: {explanation}")
                return {"success": True, "explanation": explanation}
            
            return {"success": False, "error": "Failed to generate explanation"}

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request error: {str(e)}")
            return {"success": False, "error": f"API request failed: {str(e)}"}