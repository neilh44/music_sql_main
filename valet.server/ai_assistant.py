import logging
from typing import Dict, Any, List, Optional
import requests
from dataclasses import dataclass
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import re


@dataclass
class AssistantContext:
    """Store context information for the assistant"""
    last_query: Optional[str] = None
    last_topic: Optional[str] = None
    last_entities: List[Dict[str, str]] = None
    conversation_history: List[Dict[str, Any]] = None

class ContextualSuggestionGenerator:
    @staticmethod
    def generate_suggestions(context: AssistantContext, user_query: str, is_error: bool = False) -> List[str]:
        """
        Generate contextual suggestions based on query history and current context
        
        Args:
            context (AssistantContext): Current conversation context
            user_query (str): Current user query
            is_error (bool): Whether the query resulted in an error
        
        Returns:
            List of contextual suggestions
        """
        suggestions = []
        
        # Error-specific suggestions
        if is_error:
            suggestions.extend(ContextualSuggestionGenerator._generate_error_suggestions(user_query))
        
        # Context-based suggestions
        suggestions.extend(ContextualSuggestionGenerator._generate_context_suggestions(context, user_query))
        
        # Domain-specific refinement
        suggestions.extend(ContextualSuggestionGenerator._generate_domain_suggestions(user_query))
        
        # Remove duplicates while preserving order
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in unique_suggestions:
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:3]  # Limit to top 3 suggestions
    
    @staticmethod
    def _generate_error_suggestions(user_query: str) -> List[str]:
        """
        Generate suggestions for error recovery
        
        Args:
            user_query (str): Query that resulted in an error
        
        Returns:
            List of error recovery suggestions
        """
        error_suggestions = [
            "Try rephrasing your query more specifically",
            "Verify the exact data fields you're requesting",
            "Check your query syntax and data filters"
        ]
        
        # Specific error hint patterns
        error_patterns = {
            'date': ["Ensure date format matches database schema"],
            'number': ["Check numerical values and ranges"],
            'column': ["Verify column names exist in the database"]
        }
        
        for pattern, suggestions in error_patterns.items():
            if pattern in user_query.lower():
                error_suggestions.extend(suggestions)
        
        return error_suggestions
    
    @staticmethod
    def _generate_context_suggestions(context: AssistantContext, user_query: str) -> List[str]:
        """
        Generate suggestions based on conversation context
        
        Args:
            context (AssistantContext): Current conversation context
            user_query (str): Current user query
        
        Returns:
            List of context-based suggestions
        """
        context_suggestions = []
        
        # Extract key entities using simple pattern matching
        entities = re.findall(r'\b[A-Z][a-z]+\b', user_query)
        
        if entities:
            context_suggestions.extend([
                f"Get more details about {entity}" for entity in entities[:2]
            ])
        
        # Analyze recent query patterns
        if context.conversation_history:
            recent_queries = [
                entry['query'] for entry in context.conversation_history[-3:]
            ]
            context_suggestions.append("Explore related insights from recent queries")
        
        return context_suggestions
    
    @staticmethod
    def _generate_domain_suggestions(user_query: str) -> List[str]:
        """
        Generate domain-specific query refinements
        
        Args:
            user_query (str): Current user query
        
        Returns:
            List of domain refinement suggestions
        """
        domain_suggestions = []
        
        # Domain-specific suggestion mappings
        domain_keywords = {
            'sales': [
                "Compare sales across different periods", 
                "Analyze sales trends",
                "Break down sales by categories"
            ],
            'customer': [
                "Explore customer demographics", 
                "View customer segmentation",
                "Analyze customer behavior"
            ],
            'performance': [
                "Compare performance metrics", 
                "Identify top performers",
                "Drill down into performance details"
            ]
        }
        
        # Match domain keywords
        for keyword, suggestions in domain_keywords.items():
            if keyword in user_query.lower():
                domain_suggestions.extend(suggestions)
        
        return domain_suggestions



class AIAssistant:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.context = AssistantContext(
            last_query=None,
            last_topic=None,
            last_entities=[],
            conversation_history=[]
        )
        self.logger = logging.getLogger(__name__)

    def _prepare_system_rules(self) -> str:
        """Define the comprehensive system rules and guidelines for the assistant"""
        return """
        You are an AI assistant specializing in understanding and processing user queries about valet parking data. Follow these rules meticulously to ensure accuracy, efficiency, and user satisfaction:

        1. Response Format:
        - Be concise and direct, but ensure clarity and completeness of the response.
        - Remove unnecessary explanations, metadata, or jargon unless specifically requested.
        - Present numerical data (e.g., durations, costs) in a clear and user-friendly format.
        - Use structured formats (e.g., lists, tables) when summarizing complex data.

        2. Query Understanding:
        - Accurately identify key entities such as parking locations, booking IDs, vehicle details, and customer information.
        - Recognize and interpret temporal references (e.g., "next week," "yesterday," or specific dates and times).
        - Handle valet parking-specific terminology (e.g., "drop-off," "pick-up," "slots availability") with precision.
        - Ask clarifying questions if the query is ambiguous or incomplete.

        3. Follow-up Generation:
        - Suggest follow-up questions or actions based on the user's context, such as "Would you like to confirm the booking?" or "Do you need directions to the parking location?"
        - Focus on providing practical, data-driven insights, such as slot availability, pricing comparisons, or estimated wait times.
        - Ensure the continuity of the conversation by referencing previously mentioned information when appropriate.

        4. Data Handling:
        - Ensure the accuracy and consistency of data retrieved from the system or database.
        - Proactively address missing or null values by suggesting alternative data or notifying the user.
        - Use standardized date and time formats (e.g., YYYY-MM-DD for dates and HH:MM AM/PM for times).
        - Handle user-provided data carefully, validating entries such as license plates, phone numbers, or booking references.

        5. Error Handling:
        - Provide clear, user-friendly error messages that explain the issue and guide the user toward resolution.
        - Suggest corrections for common mistakes, such as misspelled location names or invalid booking IDs.
        - Maintain the conversation flow even after an error, offering alternative solutions or rephrasing the query for better results.

        6. Booking Management:
        - Assist users in booking valet parking slots, modifying bookings, or canceling reservations.
        - Confirm all actions explicitly, summarizing the details before finalizing a booking or change.
        - Handle real-time slot availability updates, ensuring users are informed of the most current options.

        7. Pricing and Payment:
        - Provide detailed pricing information, including breakdowns (e.g., base fee, taxes, additional charges).
        - Assist with payment-related queries, such as payment methods or receipt generation.
        - Address promotional offers, discounts, or loyalty benefits where applicable.

        8. Location Assistance:
        - Offer precise directions to parking locations using address details or map links.
        - Provide information on nearby landmarks or points of interest to help users navigate.
        - Mention facilities available at each location (e.g., EV charging, covered parking).

        9. Vehicle Information:
        - Handle queries related to vehicle types, size restrictions, or special requirements (e.g., oversized vehicles).
        - Record and retrieve vehicle details accurately for booking or ticket generation.

        10. Privacy and Security:
            - Protect user data and adhere to relevant privacy policies.
            - Ensure sensitive data such as payment details or personal information is not shared inadvertently.
            - Avoid storing unnecessary data beyond the scope of the user's query.

        11. System Reliability:
            - Ensure responses are based on the most current data available in the system.
            - Handle scenarios where the system is temporarily unavailable by offering alternatives or notifying the user appropriately.
            - Proactively monitor system downtime and inform users of expected resolution times.

        By adhering to these rules, provide an efficient, user-focused valet parking assistant experience that meets user needs while maintaining reliability and clarity.
        """

    def _generate_followup_questions(self, query_result: Dict[str, Any], original_query: str) -> List[str]:
        """Generate contextual follow-up questions based on the current query and results"""
        prompt = f"""
        Based on the following query and results, suggest 2-3 relevant follow-up questions:
        
        Original Query: {original_query}
        Query Results: {query_result}
        
        Generate questions that would provide additional valuable insights.
        Return only the questions without any additional text or formatting.
        """

        try:
            response = self._send_llm_request(prompt, max_tokens=200, temperature=0.7)
            questions = [q.strip() for q in response.split('\n') if q.strip()]
            return questions[:3]  # Limit to top 3 questions
        except Exception as e:
            self.logger.error(f"Error generating follow-up questions: {e}")
            return []

    def _send_llm_request(self, prompt: str, max_tokens: int = 500, temperature: float = 0.3) -> str:
        """Send request to LLM and handle response"""
        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": self._prepare_system_rules()},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and result['choices']:
                return result['choices'][0]['message']['content'].strip()
            return ""
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"LLM request error: {e}")
            raise

    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process user query and maintain context"""
        try:
            # Update context
            self.context.last_query = user_query
            self.context.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "query": user_query,
                "role": "user"
            })

            # Process query with LLM
            processed_response = self._send_llm_request(user_query)
            
            # Generate follow-up questions
            followups = self._generate_followup_questions(
                {"response": processed_response}, 
                user_query
            )

            # Update conversation history with response
            self.context.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "response": processed_response,
                "followups": followups,
                "role": "assistant"
            })

            return {
                "success": True,
                "response": processed_response,
                "followup_questions": followups,
                "context": {
                    "last_query": self.context.last_query,
                    "last_topic": self.context.last_topic
                }
            }

        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return {
                "success": False,
                "error": str(e),
                "context": self.context
            }

    def refine_response(self, llm_response: str) -> str:
        """Clean and format LLM response for user consumption"""
        # Remove common LLM artifacts
        cleaned = llm_response.replace("```", "").strip()
        
        # Remove any system prompts that might have leaked
        if "You are an AI assistant" in cleaned:
            cleaned = cleaned.split("You are an AI assistant")[1]
        
        # Format numerical values and dates
        # (Add specific formatting logic based on your needs)
        
        return cleaned.strip()

    def handle_error(self, error: str) -> Dict[str, Any]:
        """Generate user-friendly error messages and recovery suggestions"""
        error_prompt = f"""
        Generate a user-friendly error message and recovery suggestion for:
        {error}
        
        Format: Brief error explanation followed by a helpful suggestion.
        """
        
        try:
            response = self._send_llm_request(error_prompt, max_tokens=150, temperature=0.3)
            return {
                "error_message": self.refine_response(response),
                "original_error": error,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error handling error message: {e}")
            return {
                "error_message": "An unexpected error occurred. Please try rephrasing your query.",
                "original_error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        

class EnhancedSuggestionGenerator:
    @staticmethod
    def generate_comprehensive_suggestions(
        context: Dict[str, Any], 
        user_query: str, 
        response: str = None, 
        error: str = None
    ) -> Dict[str, List[str]]:
        """
        Generate comprehensive suggestions based on context, query, response, or error.
        
        Args:
            context (Dict): Conversation context
            user_query (str): Current user query
            response (str, optional): LLM response
            error (str, optional): Error message
        
        Returns:
            Dict of suggestion categories with lists of suggestions
        """
        suggestions = {
            'follow_up_questions': [],
            'query_refinements': [],
            'error_recovery': [],
            'related_insights': []
        }
        
        # Error-specific suggestions
        if error:
            suggestions['error_recovery'] = EnhancedSuggestionGenerator._generate_error_suggestions(error)
        
        # Query analysis
        query_keywords = EnhancedSuggestionGenerator._extract_keywords(user_query)
        
        # Response-based suggestions
        if response:
            suggestions['follow_up_questions'] = EnhancedSuggestionGenerator._generate_response_followups(
                response, query_keywords
            )
            suggestions['related_insights'] = EnhancedSuggestionGenerator._generate_related_insights(
                response, query_keywords
            )
        
        # Query refinement suggestions
        suggestions['query_refinements'] = EnhancedSuggestionGenerator._generate_query_refinements(
            user_query, query_keywords
        )
        
        return suggestions
    
    @staticmethod
    def _extract_keywords(query: str) -> List[str]:
        """
        Extract meaningful keywords from the query
        
        Args:
            query (str): User query
        
        Returns:
            List of extracted keywords
        """
        # Remove stop words and extract significant terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        keywords = [
            word.lower() for word in re.findall(r'\b\w+\b', query) 
            if word.lower() not in stop_words and len(word) > 2
        ]
        return list(set(keywords))
    
    @staticmethod
    def _generate_error_suggestions(error: str) -> List[str]:
        """
        Generate sophisticated error recovery suggestions
        
        Args:
            error (str): Error message
        
        Returns:
            List of error recovery suggestions
        """
        error_patterns = {
            'connection': [
                "Check your internet connection",
                "Retry the request after a moment",
                "Verify API endpoint accessibility"
            ],
            'authorization': [
                "Validate your authentication credentials",
                "Check API key permissions",
                "Contact system administrator"
            ],
            'data': [
                "Verify input data format",
                "Ensure all required fields are provided",
                "Check data constraints and validation"
            ]
        }
        
        suggestions = []
        for pattern, pattern_suggestions in error_patterns.items():
            if pattern in error.lower():
                suggestions.extend(pattern_suggestions)
        
        # Generic fallback suggestions
        if not suggestions:
            suggestions = [
                "Try rephrasing your query",
                "Check query syntax and parameters",
                "Verify data input"
            ]
        
        return suggestions[:3]
    
    @staticmethod
    def _generate_response_followups(response: str, keywords: List[str]) -> List[str]:
        """
        Generate follow-up questions based on response content
        
        Args:
            response (str): LLM response
            keywords (List[str]): Query keywords
        
        Returns:
            List of follow-up question suggestions
        """
        followup_templates = [
            "Can you provide more details about {keyword}?",
            "What are the implications of {keyword} in this context?",
            "How does {keyword} impact the overall situation?",
            "Are there any additional insights about {keyword}?"
        ]
        
        followups = []
        for keyword in keywords[:2]:  # Limit to top 2 keywords
            for template in followup_templates:
                followups.append(template.format(keyword=keyword.capitalize()))
        
        return followups[:3]
    
    @staticmethod
    def _generate_related_insights(response: str, keywords: List[str]) -> List[str]:
        """
        Generate related insights based on response and keywords
        
        Args:
            response (str): LLM response
            keywords (List[str]): Query keywords
        
        Returns:
            List of related insight suggestions
        """
        related_insight_templates = [
            "Explore broader context of {keyword}",
            "Compare {keyword} with alternative perspectives",
            "Investigate long-term trends in {keyword}"
        ]
        
        insights = []
        for keyword in keywords[:2]:  # Limit to top 2 keywords
            for template in related_insight_templates:
                insights.append(template.format(keyword=keyword.capitalize()))
        
        return insights[:3]
    
    @staticmethod
    def _generate_query_refinements(query: str, keywords: List[str]) -> List[str]:
        """
        Generate query refinement suggestions
        
        Args:
            query (str): Original user query
            keywords (List[str]): Extracted keywords
        
        Returns:
            List of query refinement suggestions
        """
        refinement_strategies = [
            "Add more specific context to your query",
            "Include additional details or constraints",
            "Clarify the specific information you're seeking"
        ]
        
        keyword_refinements = [
            f"Try specifying more about {keyword}" for keyword in keywords[:2]
        ]
        
        return refinement_strategies[:2] + keyword_refinements
    
class ResponseRepresenter:
    @staticmethod
    def analyze_response_type(llm_response: str) -> dict:
        """
        Analyze the LLM response to determine the most appropriate representation method.
        
        Args:
            llm_response (str): The response from the LLM
        
        Returns:
            dict: A dictionary with recommended representation method and details
        """
        # Preprocessing and initial analysis
        clean_response = llm_response.lower().strip()
        
        # Define patterns and keywords for different representation types
        representation_rules = {
            'numerical_data': {
                'patterns': [
                    r'\d+(\.\d+)?%?',  # Percentages or numeric values
                    r'(\d+\s*to\s*\d+)',  # Range of numbers
                ],
                'keywords': ['percent', 'percentage', 'ratio', 'average', 'total']
            },
            'comparative_data': {
                'patterns': [
                    r'compared\s+to',
                    r'more\s+than',
                    r'less\s+than'
                ],
                'keywords': ['comparison', 'difference', 'contrast']
            },
            'trend_data': {
                'patterns': [
                    r'increasing',
                    r'decreasing',
                    r'trend',
                    r'over\s+time'
                ],
                'keywords': ['trend', 'pattern', 'change', 'evolution']
            }
        }
        
        # Scoring mechanism to determine representation
        representation_scores = {
            'text': 1,
            'bar_graph': 0,
            'line_graph': 0,
            'pie_chart': 0,
            'heatmap': 0
        }
        
        # Check patterns and keywords
        for rep_type, rules in representation_rules.items():
            pattern_matches = sum(1 for pattern in rules['patterns'] if re.search(pattern, clean_response))
            keyword_matches = sum(1 for keyword in rules['keywords'] if keyword in clean_response)
            
            total_score = pattern_matches * 2 + keyword_matches
            
            # Assign representation preferences based on scoring
            if rep_type == 'numerical_data':
                representation_scores['bar_graph'] += total_score
                representation_scores['pie_chart'] += total_score // 2
            
            if rep_type == 'comparative_data':
                representation_scores['bar_graph'] += total_score * 2
                representation_scores['line_graph'] += total_score
            
            if rep_type == 'trend_data':
                representation_scores['line_graph'] += total_score * 2
                representation_scores['heatmap'] += total_score
        
        # Determine best representation
        best_representation = max(representation_scores, key=representation_scores.get)
        
        return {
            'recommended_representation': best_representation,
            'confidence_score': representation_scores[best_representation],
            'raw_analysis': representation_scores
        }
    
    @staticmethod
    def represent_response(llm_response: str, response_analysis: dict) -> dict:
        """
        Generate appropriate representation based on the analysis.
        
        Args:
            llm_response (str): The LLM response
            response_analysis (dict): Analysis from analyze_response_type
        
        Returns:
            dict: Representation details and potential visualization
        """
        representation_method = response_analysis['recommended_representation']
        
        if representation_method == 'text':
            return {
                'type': 'text',
                'content': llm_response
            }
        
        if representation_method == 'bar_graph':
            # Extract numeric data
            numbers = re.findall(r'\d+(\.\d+)?', llm_response)
            if numbers:
                numbers = [float(n) for n in numbers]
                
                plt.figure(figsize=(10, 5))
                plt.bar(range(len(numbers)), numbers)
                plt.title('Data Representation')
                plt.xlabel('Categories')
                plt.ylabel('Values')
                plt.tight_layout()
                
                # Save plot to a bytes buffer for transmission
                from io import BytesIO
                buf = BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                
                return {
                    'type': 'bar_graph',
                    'data': numbers,
                    'image_bytes': buf.getvalue()
                }
        
        if representation_method == 'line_graph':
            # Extract trend data
            numbers = re.findall(r'\d+(\.\d+)?', llm_response)
            if numbers:
                numbers = [float(n) for n in numbers]
                
                plt.figure(figsize=(10, 5))
                plt.plot(range(len(numbers)), numbers, marker='o')
                plt.title('Trend Analysis')
                plt.xlabel('Time/Sequence')
                plt.ylabel('Values')
                plt.tight_layout()
                
                buf = BytesIO()
                plt.savefig(buf, format='png')
                buf.seek(0)
                
                return {
                    'type': 'line_graph',
                    'data': numbers,
                    'image_bytes': buf.getvalue()
                }
        
        # Default to text if no specific representation found
        return {
            'type': 'text',
            'content': llm_response
        }

# Example usage
def process_llm_response(llm_response):
    representer = ResponseRepresenter()
    
    # Analyze response type
    analysis = representer.analyze_response_type(llm_response)
    
    # Generate representation
    representation = representer.represent_response(llm_response, analysis)
    
    return {
        'original_response': llm_response,
        'representation_analysis': analysis,
        'representation': representation
    }