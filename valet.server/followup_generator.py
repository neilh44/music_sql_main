from typing import List, Dict, Any
import re
from datetime import datetime

class FollowUpQuestionGenerator:
    def __init__(self):
        # Define common patterns for different types of queries
        self.query_patterns = {
            'availability': r'(available|empty|free|open)',
            'duration': r'(time|duration|long|hours)',
            'cost': r'(cost|price|rate|fee|charge)',
            'location': r'(location|where|spot|level|floor)',
            'vehicle': r'(car|vehicle|automobile)',
            'trend': r'(trend|pattern|history)',
            'comparison': r'(compare|difference|versus|vs)',
            'status': r'(status|state|condition)'
        }
        
        # Define schema-based follow-up templates
        self.schema_templates = {
            'parking_spots': [
                "Would you like to know about available spots in a specific level?",
                "Should we check the availability during a different time period?",
                "Would you like to see spots with specific features (e.g., handicap accessible, EV charging)?",
                "Would you like to compare availability across different parking levels?"
            ],
            'vehicles': [
                "Would you like to see the parking history for specific vehicle types?",
                "Should we check the average parking duration for this vehicle category?",
                "Would you like to know about common parking patterns for similar vehicles?",
                "Should we look at peak parking times for this type of vehicle?"
            ],
            'transactions': [
                "Would you like to see the cost breakdown for different durations?",
                "Should we analyze the payment patterns over a specific time period?",
                "Would you like to compare rates between different parking spots?",
                "Should we look at popular payment methods used?"
            ],
            'occupancy': [
                "Would you like to see occupancy trends during peak hours?",
                "Should we analyze the occupancy patterns for specific days of the week?",
                "Would you like to compare occupancy rates between different levels?",
                "Should we look at how occupancy affects pricing?"
            ]
        }

    def analyze_query_type(self, query: str) -> List[str]:
        """Analyze the query to determine its type based on patterns"""
        query_types = []
        for pattern_type, pattern in self.query_patterns.items():
            if re.search(pattern, query.lower()):
                query_types.append(pattern_type)
        return query_types

    def generate_followup_questions(
        self,
        current_query: str,
        conversation_context: List[Dict[str, Any]],
        results: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate context-aware follow-up questions"""
        
        # If no results, return clarification questions
        if not results:
            return [
                "Could you please provide more specific details about what you're looking for?",
                "Would you like to try a different way to phrase your question?",
                "Should we look for similar information using different criteria?"
            ]

        query_types = self.analyze_query_type(current_query)
        followup_questions = set()  # Use set to avoid duplicates

        # Generate questions based on query type
        for query_type in query_types:
            if query_type == 'availability':
                followup_questions.update([
                    "Would you like to check availability for a different time slot?",
                    "Should we look at availability in nearby parking spots?"
                ])
            elif query_type == 'duration':
                followup_questions.update([
                    "Would you like to see average parking durations for this spot?",
                    "Should we analyze peak parking duration patterns?"
                ])
            elif query_type == 'cost':
                followup_questions.update([
                    "Would you like to compare rates with similar parking spots?",
                    "Should we look at cost variations during peak hours?"
                ])

        # Add schema-based questions
        for table, templates in self.schema_templates.items():
            # Check if the current query or recent context involves this table
            if any(table in str(context.get('sql', '')).lower() 
                  for context in conversation_context[-3:]):  # Look at last 3 interactions
                followup_questions.update(templates[:2])  # Add up to 2 relevant templates

        # Add trend/pattern questions if there's sufficient data
        if len(results) > 1:
            followup_questions.add(
                "Would you like to see any trends or patterns in this data?"
            )

        # Add comparison questions if appropriate
        if len(results) > 1 and 'comparison' not in query_types:
            followup_questions.add(
                "Would you like to compare these results with other periods or categories?"
            )

        # Prioritize and limit questions
        final_questions = list(followup_questions)[:4]  # Limit to top 4 questions

        return final_questions

    def generate_exploration_questions(self, table_name: str) -> List[str]:
        """Generate exploration questions for a specific table"""
        return self.schema_templates.get(table_name, [
            f"What would you like to know about the {table_name}?",
            f"Should we analyze any specific patterns in {table_name}?",
            f"Would you like to see a summary of {table_name}?"
        ])