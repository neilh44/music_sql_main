import logging
from typing import List, Dict, Any, Optional, Union
import json
from datetime import datetime
from groq import Groq
import re
from collections import Counter

class FollowUpQuestionGenerator:
    """
    A class to generate contextual follow-up questions using LLM (Groq/Llama) 
    for a parking management system.
    """
    
    def __init__(self, api_key: str, model: str = "llama3-8b-8192"):
        """
        Initialize the LLM Follow-up Generator.
        
        Args:
            api_key (str): API key for Groq
            model (str): Model identifier to use (default: llama3-8b-8192)
        """
        self.client = Groq(api_key=api_key)
        self.model = model
        self.logger = logging.getLogger(__name__)
        
        # Configure logging
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Database schema definition
        self.schema = {
            "parking_spots": {
                "description": "Information about individual parking spots",
                "columns": {
                    "spot_id": "INTEGER PRIMARY KEY",
                    "level": "INTEGER",
                    "section": "TEXT",
                    "type": "TEXT",
                    "is_handicap": "BOOLEAN",
                    "has_ev_charging": "BOOLEAN",
                    "status": "TEXT"
                },
                "relationships": [
                    "vehicles (current occupancy)",
                    "transactions (parking history)",
                    "occupancy_history (historical data)"
                ]
            },
            "vehicles": {
                "description": "Information about vehicles using the parking facility",
                "columns": {
                    "vehicle_id": "INTEGER PRIMARY KEY",
                    "type": "TEXT",
                    "color": "TEXT",
                    "license_plate": "TEXT",
                    "entry_time": "TIMESTAMP",
                    "expected_exit_time": "TIMESTAMP"
                },
                "relationships": [
                    "parking_spots (current location)",
                    "transactions (parking history)"
                ]
            },
            "transactions": {
                "description": "Parking transaction records",
                "columns": {
                    "transaction_id": "INTEGER PRIMARY KEY",
                    "vehicle_id": "INTEGER",
                    "spot_id": "INTEGER",
                    "entry_time": "TIMESTAMP",
                    "exit_time": "TIMESTAMP",
                    "amount": "DECIMAL",
                    "payment_method": "TEXT"
                },
                "relationships": [
                    "vehicles (vehicle details)",
                    "parking_spots (spot details)"
                ]
            },
            "occupancy_history": {
                "description": "Historical occupancy data for parking spots",
                "columns": {
                    "timestamp": "TIMESTAMP",
                    "spot_id": "INTEGER",
                    "is_occupied": "BOOLEAN",
                    "vehicle_id": "INTEGER",
                    "duration": "INTEGER"
                },
                "relationships": [
                    "parking_spots (spot details)",
                    "vehicles (vehicle details)"
                ]
            }
        }

    def _identify_topic(self, query: str) -> Dict[str, float]:
        """
        Identify topics and their relevance scores in a query.
        
        Args:
            query (str): The user's query
            
        Returns:
            Dict[str, float]: Dictionary of topics and their relevance scores
        """
        topics = {
            "availability": ["available", "vacant", "empty", "open", "free", "full"],
            "vehicle": ["car", "vehicle", "parked", "parking", "automobile"],
            "cost": ["price", "rate", "fee", "cost", "charge", "payment"],
            "occupancy": ["occupancy", "filled", "capacity", "usage", "utilization"],
            "time": ["duration", "hours", "time", "period", "schedule"],
            "location": ["level", "floor", "section", "area", "spot", "zone"],
            "features": ["ev", "charging", "handicap", "disabled", "special"]
        }
        
        query_lower = query.lower()
        scores = {}
        
        for topic, keywords in topics.items():
            # Calculate relevance score based on keyword matches
            matches = sum(keyword in query_lower for keyword in keywords)
            if matches:
                scores[topic] = matches / len(keywords)
        
        return scores

    def _analyze_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze query results for patterns and insights.
        
        Args:
            results (List[Dict[str, Any]]): Query results to analyze
            
        Returns:
            Dict[str, Any]: Analysis of the results
        """
        analysis = {
            "record_count": len(results),
            "fields": [],
            "patterns": {},
            "temporal_analysis": {},
            "categorical_analysis": {}
        }
        
        if not results:
            return analysis
            
        # Analyze structure
        sample = results[0]
        analysis["fields"] = list(sample.keys())
        
        # Look for temporal patterns
        time_fields = [k for k in sample.keys() 
                      if any(t in k.lower() 
                            for t in ["time", "date", "timestamp"])]
        
        if time_fields:
            analysis["temporal_analysis"] = {
                "has_temporal_data": True,
                "temporal_fields": time_fields
            }
        
        # Analyze categorical data
        for key in sample.keys():
            values = [str(r.get(key)) for r in results]
            unique_values = set(values)
            
            if 1 < len(unique_values) <= 10:  # Reasonable number of categories
                value_counts = Counter(values)
                analysis["categorical_analysis"][key] = {
                    "unique_values": len(unique_values),
                    "most_common": value_counts.most_common(3)
                }
        
        return analysis

    def _extract_entities(self, query: str) -> Dict[str, str]:
        """
        Extract relevant entities from the query.
        
        Args:
            query (str): The user's query
            
        Returns:
            Dict[str, str]: Extracted entities and their values
        """
        entities = {}
        
        # Extract colors
        colors = ["blue", "red", "green", "yellow", "black", "white", "silver"]
        color_pattern = r'\b(' + '|'.join(colors) + r')\b'
        color_match = re.search(color_pattern, query.lower())
        if color_match:
            entities["color"] = color_match.group(1)
        
        # Extract levels
        level_pattern = r'\b(?:level|floor)\s*(\d+)\b'
        level_match = re.search(level_pattern, query.lower())
        if level_match:
            entities["level"] = level_match.group(1)
        
        # Extract vehicle types
        vehicle_types = ["car", "truck", "van", "motorcycle", "bike"]
        vehicle_pattern = r'\b(' + '|'.join(vehicle_types) + r')\b'
        vehicle_match = re.search(vehicle_pattern, query.lower())
        if vehicle_match:
            entities["vehicle_type"] = vehicle_match.group(1)
        
        return entities

    def _format_conversation_history(
        self, 
        conversation_context: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Format conversation history for LLM context.
        
        Args:
            conversation_context (List[Dict[str, Any]]): Raw conversation history
            
        Returns:
            List[Dict[str, Any]]: Formatted conversation history
        """
        formatted_history = []
        
        for ctx in conversation_context[-3:]:  # Last 3 interactions
            topics = self._identify_topic(ctx.get("query", ""))
            entities = self._extract_entities(ctx.get("query", ""))
            
            interaction = {
                "query": ctx.get("query", ""),
                "timestamp": ctx.get("timestamp", datetime.now().isoformat()),
                "topics": topics,
                "entities": entities,
                "result_summary": self._summarize_results(ctx.get("results", []))
            }
            formatted_history.append(interaction)
        
        return formatted_history

    def _summarize_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a summary of query results.
        
        Args:
            results (List[Dict[str, Any]]): Query results to summarize
            
        Returns:
            Dict[str, Any]: Summary of the results
        """
        if not results:
            return {"status": "no_results"}
            
        summary = {
            "record_count": len(results),
            "fields_present": list(results[0].keys()) if results else [],
            "sample_size": min(len(results), 3),
            "analysis": self._analyze_results(results)
        }
        
        return summary

    def prepare_llm_prompt(
        self,
        current_query: str,
        conversation_context: List[Dict[str, Any]],
        results: List[Dict[str, Any]]
    ) -> str:
        """
        Prepare the prompt for the LLM with all relevant context.
        
        Args:
            current_query (str): The current user query
            conversation_context (List[Dict[str, Any]]): Conversation history
            results (List[Dict[str, Any]]): Current query results
            
        Returns:
            str: Formatted prompt for the LLM
        """
        # Format context
        formatted_history = self._format_conversation_history(conversation_context)
        current_topics = self._identify_topic(current_query)
        current_entities = self._extract_entities(current_query)
        results_analysis = self._analyze_results(results)
        
        # Create the structured prompt
        prompt = f"""As a parking management system assistant, generate relevant follow-up questions based on this context:

Current Query: "{current_query}"

Topics Identified: {json.dumps(current_topics, indent=2)}
Entities Identified: {json.dumps(current_entities, indent=2)}

Database Schema:
{json.dumps(self.schema, indent=2)}

Recent Conversation History:
{json.dumps(formatted_history, indent=2)}

Current Results Analysis:
{json.dumps(results_analysis, indent=2)}

Generate 4 natural, contextually relevant follow-up questions that:
1. Build upon the current query topics ({', '.join(current_topics.keys())})
2. Explore relevant relationships in the database schema
3. Help users discover patterns in the data
4. Consider the conversation history and current entities

Important:
- Questions should be specific and actionable
- Reference actual data patterns where relevant
- Maintain context from the conversation history
- Consider temporal and categorical patterns in results
- Integrate relevant schema relationships

Format the response as a JSON array of strings containing exactly 4 questions.
"""
        return prompt

    async def generate_followup_questions(
        self,
        current_query: str,
        conversation_context: List[Dict[str, Any]],
        results: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate follow-up questions using the LLM.
        
        Args:
            current_query (str): The current user query
            conversation_context (List[Dict[str, Any]]): Conversation history
            results (List[Dict[str, Any]]): Current query results
            
        Returns:
            List[str]: Generated follow-up questions
        """
        try:
            # Log generation attempt
            self.logger.info(f"Generating follow-up questions for query: {current_query}")
            
            # Prepare the prompt
            prompt = self.prepare_llm_prompt(
                current_query,
                conversation_context,
                results
            )

            # Call the LLM
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant generating follow-up questions for a parking management system. Generate natural, contextually relevant questions that help users explore the data and discover insights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=300
            )

            # Parse the response
            try:
                questions = json.loads(completion.choices[0].message.content)
                
                # Validate and clean questions
                if not isinstance(questions, list):
                    raise ValueError("LLM response is not a list")
                    
                questions = [
                    str(q).strip() 
                    for q in questions 
                    if isinstance(q, (str, int, float))
                ]
                
                # Ensure exactly 4 questions
                while len(questions) < 4:
                    questions.append(self._get_fallback_question())
                questions = questions[:4]
                
                self.logger.info("Successfully generated follow-up questions")
                return questions
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
                return self._get_fallback_questions()

        except Exception as e:
            self.logger.error(f"Error generating follow-up questions: {str(e)}")
            return self._get_fallback_questions()

    def _get_fallback_questions(self) -> List[str]:
        """
        Get fallback questions in case of errors.
        
        Returns:
            List[str]: List of fallback questions
        """
        return [
            "Would you like to know about current parking availability?",
            "Should we check the parking rates and fees?",
            "Would you like to see occupancy trends over time?",
            "Should we look at specific vehicle types or features?"
        ]

    def _get_fallback_question(self) -> str:
        """
        Get a single fallback question.
        
        Returns:
            str: A fallback question
        """
        import random
        fallback_questions = [
            "Would you like to explore a different aspect of the parking data?",
            "Should we analyze any specific patterns in these results?",
            "Would you like to see how this compares to overall trends?",
            "Should we look at related information from the database?"
        ]
        return random.choice(fallback_questions)