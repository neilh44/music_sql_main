import random
import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from groq import Groq
import sqlite3
from collections import Counter
from dataclasses import dataclass

@dataclass
class QueryComponents:
    action: str
    subject: str
    filters: List[Dict[str, str]]
    aggregation: Optional[str]
    order: Optional[str]
    limit: Optional[int]

class QueryAnalyzer:
    def __init__(self):
        self.action_verbs = {
            'show': 'SELECT',
            'give': 'SELECT',
            'find': 'SELECT',
            'list': 'SELECT',
            'count': 'COUNT',
            'get': 'SELECT',
            'display': 'SELECT',
            'tell': 'SELECT'
        }
        
        self.aggregation_keywords = {
            'count': 'COUNT',
            'highest': 'MAX',
            'maximum': 'MAX',
            'lowest': 'MIN',
            'minimum': 'MIN',
            'average': 'AVG',
            'total': 'SUM'
        }
        
        self.filter_keywords = {
            'color': ['color', 'colored'],
            'type': ['type', 'category', 'kind'],
            'status': ['status', 'state', 'condition']
        }
        
        self.common_adjectives = [
            'red', 'blue', 'green', 'black', 'white',
            'new', 'old', 'available', 'occupied',
            'compact', 'large', 'small'
        ]

    def analyze_query(self, query: str) -> QueryComponents:
        query = query.lower().strip()
        words = query.split()
        
        action = self._extract_action(words)
        aggregation = self._extract_aggregation(query)
        filters = self._extract_filters(query)
        subject = self._extract_subject(query)
        order = "DESC" if any(word in query for word in ['highest', 'most', 'maximum']) else None
        limit = 1 if order else None
        
        return QueryComponents(
            action=action,
            subject=subject,
            filters=filters,
            aggregation=aggregation,
            order=order,
            limit=limit
        )

    def _extract_action(self, words: List[str]) -> str:
        for word in words:
            if word in self.action_verbs:
                return self.action_verbs[word]
        return 'SELECT'

    def _extract_aggregation(self, query: str) -> Optional[str]:
        for keyword, agg_type in self.aggregation_keywords.items():
            if keyword in query:
                return agg_type
        return None

    def _extract_filters(self, query: str) -> List[Dict[str, str]]:
        filters = []
        words = query.split()
        
        for i, word in enumerate(words):
            if word in self.common_adjectives:
                if i + 1 < len(words) and words[i + 1] in self.filter_keywords['color']:
                    filters.append({'field': 'color', 'value': word})
                    continue
                if i > 0 and words[i - 1] in self.filter_keywords['color']:
                    filters.append({'field': 'color', 'value': word})
        
        for type_keyword in self.filter_keywords['type']:
            if type_keyword in query:
                idx = query.find(type_keyword)
                remaining = query[idx + len(type_keyword):].strip().split()
                if remaining:
                    filters.append({'field': 'type', 'value': remaining[0]})
        
        return filters

    def _extract_subject(self, query: str) -> str:
        subjects = ['car', 'cars', 'vehicle', 'vehicles', 'space', 'spaces', 
                   'spot', 'spots', 'user', 'users', 'activity', 'activities']
        
        words = query.split()
        for word in words:
            if word in subjects:
                return word
        return 'cars'

class FollowUpQuestionGenerator:
    def __init__(self, api_key: str, db_path: str = "./data/sqlite.db", model: str = "llama2-70b-4096"):
        """Initialize the generator with required credentials and settings."""
        self.client = Groq(api_key=api_key)
        self.model = model
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.query_analyzer = QueryAnalyzer()
        
        # Configure logging
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Get database schema
        self.schema = self._get_db_schema()

    def _get_db_schema(self) -> Dict[str, Any]:
        """Fetch and return the database schema."""
        schema = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                    foreign_keys = cursor.fetchall()
                    
                    schema[table_name] = {
                        "description": f"Information about {table_name}",
                        "columns": {col[1]: col[2] for col in columns},
                        "relationships": [
                            f"{fk[2]} ({fk[3]} -> {fk[4]})" 
                            for fk in foreign_keys
                        ]
                    }
            return schema
            
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {str(e)}")
            return {}
        except Exception as e:
            self.logger.error(f"Error fetching schema: {str(e)}")
            return {}

    def _extract_json_array(self, text: str) -> List[str]:
        """Extract a JSON array from text that might contain additional content."""
        try:
            # Try to parse the entire response as JSON first
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                # Find the JSON array in the text
                start_idx = text.find('[')
                end_idx = text.rfind(']') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = text[start_idx:end_idx]
                    return json.loads(json_str)
                else:
                    self.logger.error(f"Could not find JSON array in response: {text}")
                    return []
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse extracted JSON: {str(e)}")
                return []

    def _get_query_analysis(self, query: str) -> Dict[str, Any]:
        """Analyze the query using QueryAnalyzer."""
        components = self.query_analyzer.analyze_query(query)
        return {
            "action": components.action,
            "subject": components.subject,
            "filters": components.filters,
            "aggregation": components.aggregation,
            "order": components.order
        }

    def _identify_topic(self, query: str) -> Dict[str, float]:
        """Identify topics based on database schema."""
        if not self.schema:
            return {}
            
        query_lower = query.lower()
        scores = {}
        
        for table_name, table_info in self.schema.items():
            if table_name.replace('_', ' ') in query_lower:
                scores[table_name] = 1.0
                
            column_matches = sum(
                1 for col_name in table_info['columns'].keys()
                if col_name.replace('_', ' ') in query_lower
            )
            if column_matches:
                scores[table_name] = column_matches / len(table_info['columns'])
                
            for col_name, col_type in table_info['columns'].items():
                if any(term in col_name.lower() for term in ['time', 'date']) and \
                   any(term in query_lower for term in ['when', 'time', 'date', 'duration']):
                    scores[f"{table_name}_temporal"] = 1.0
                
                if col_type.upper() in ['INTEGER', 'DECIMAL', 'FLOAT'] and \
                   any(term in query_lower for term in ['how many', 'count', 'total', 'average']):
                    scores[f"{table_name}_metrics"] = 1.0
                    
            for relationship in table_info.get('relationships', []):
                if any(term in query_lower for term in relationship.lower().split()):
                    scores[f"{table_name}_relations"] = 1.0
        
        return scores

    def prepare_llm_prompt(
        self,
        current_query: str,
        conversation_context: List[Dict[str, Any]],
        results: List[Dict[str, Any]]
    ) -> str:
        """Prepare the prompt for the LLM."""
        query_analysis = self._get_query_analysis(current_query)
        current_topics = self._identify_topic(current_query)
        
        prompt = f"""IMPORTANT: You must respond ONLY with a JSON array containing exactly 4 questions. Do not include any additional text before or after the array.

Current Query: "{current_query}"

Query Analysis:
- Action: {query_analysis['action']}
- Subject: {query_analysis['subject']}
- Filters: {json.dumps(query_analysis['filters'], indent=2)}
- Aggregation: {query_analysis['aggregation']}
- Order: {query_analysis['order']}

Topics Identified: {json.dumps(current_topics, indent=2)}

Database Schema:
{json.dumps(self.schema, indent=2)}

Generate 4 follow-up questions that:
1. Build upon the current action ({query_analysis['action']}) and subject ({query_analysis['subject']})
2. Explore different aspects of the {query_analysis['subject']} in our database
3. Consider variations of the current filters and aggregations
4. Suggest related queries based on the database schema relationships

Return ONLY a JSON array in this exact format:
[
    "First follow-up question about {query_analysis['subject']}?",
    "Second follow-up question exploring a different aspect?",
    "Third follow-up question considering variations?",
    "Fourth follow-up question about related data?"
]"""
        return prompt

    def _get_fallback_questions(self) -> List[str]:
        """Get a list of fallback questions when generation fails."""
        return [
            "Would you like to see the parking occupancy for a different time period?",
            "Should we analyze the data by vehicle type instead?",
            "Would you like to see trends over time for this metric?",
            "Should we look at related statistics from other areas?"
        ]

    def _get_fallback_question(self) -> str:
        """Get a single fallback question."""
        return random.choice(self._get_fallback_questions())

    def generate_followup_questions(
        self,
        current_query: str,
        conversation_context: List[Dict[str, Any]],
        results: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate follow-up questions using the LLM."""
        try:
            self.logger.info(f"Generating follow-up questions for query: {current_query}")
            
            # Prepare prompt
            prompt = self.prepare_llm_prompt(
                current_query,
                conversation_context,
                results
            )

            # Call LLM
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant generating follow-up questions for a parking management system. IMPORTANT: Respond ONLY with a JSON array of 4 questions. Do not include any additional text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=300
            )

            # Extract and process questions
            response_content = completion.choices[0].message.content.strip()
            questions = self._extract_json_array(response_content)
            
            if not isinstance(questions, list) or len(questions) == 0:
                self.logger.error(f"Invalid questions format: {questions}")
                return self._get_fallback_questions()
                
            # Clean and validate questions
            questions = [str(q).strip() for q in questions if isinstance(q, (str, int, float))]
            
            # Ensure exactly 4 questions
            while len(questions) < 4:
                questions.append(self._get_fallback_question())
            return questions[:4]

        except Exception as e:
            self.logger.error(f"Error generating follow-up questions: {str(e)}")
            return self._get_fallback_questions()