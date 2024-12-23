from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

@dataclass
class Interaction:
    """Represents a single interaction in the conversation"""
    timestamp: str
    query: str
    sql_query: str
    results: List[Any]
    explanation: str
    visualization_type: Optional[str] = None
    visualization_data: Optional[Dict] = None

class ContextManager:
    def __init__(self, max_history: int = 5):
        """
        Initialize the context manager with configurable history size
        
        Args:
            max_history (int): Maximum number of interactions to store
        """
        self.max_history = max_history
        self.conversation_contexts: Dict[str, List[Interaction]] = {}
        
    def add_context(
        self,
        session_id: str,
        query: str,
        sql_query: str,
        results: List[Any],
        explanation: str,
        visualization_type: Optional[str] = None,
        visualization_data: Optional[Dict] = None
    ) -> None:
        """
        Add a new interaction to the conversation context
        
        Args:
            session_id: Unique identifier for the conversation
            query: Original natural language query
            sql_query: Generated SQL query
            results: Query execution results
            explanation: Natural language explanation
            visualization_type: Type of visualization if any
            visualization_data: Visualization data if any
        """
        if session_id not in self.conversation_contexts:
            self.conversation_contexts[session_id] = []
            
        interaction = Interaction(
            timestamp=datetime.now().isoformat(),
            query=query,
            sql_query=sql_query,
            results=results,
            explanation=explanation,
            visualization_type=visualization_type,
            visualization_data=visualization_data
        )
        
        self.conversation_contexts[session_id].append(interaction)
        
        # Maintain max history size
        if len(self.conversation_contexts[session_id]) > self.max_history:
            self.conversation_contexts[session_id].pop(0)

    def get_context(self, session_id: str, num_recent: int = 3) -> List[Dict[str, Any]]:
        """
        Get recent context for a given session
        
        Args:
            session_id: Unique identifier for the conversation
            num_recent: Number of recent interactions to include
            
        Returns:
            List of recent interactions as dictionaries
        """
        if session_id not in self.conversation_contexts:
            return []
            
        recent_interactions = self.conversation_contexts[session_id][-num_recent:]
        
        context = []
        for interaction in recent_interactions:
            context_entry = {
                "timestamp": interaction.timestamp,
                "query": interaction.query,
                "sql_query": interaction.sql_query,
                "results_summary": self._summarize_results(interaction.results),
                "explanation": interaction.explanation
            }
            
            if interaction.visualization_type:
                context_entry["visualization"] = {
                    "type": interaction.visualization_type,
                    "data": interaction.visualization_data
                }
                
            context.append(context_entry)
            
        return context

    def _summarize_results(self, results: List[Any], max_items: int = 3) -> str:
        """
        Create a brief summary of query results
        
        Args:
            results: Query results to summarize
            max_items: Maximum number of items to include in summary
            
        Returns:
            Summarized string representation of results
        """
        if not results:
            return "No results"
            
        summary = []
        for item in results[:max_items]:
            if isinstance(item, (list, tuple)):
                summary.append(", ".join(str(x) for x in item))
            else:
                summary.append(str(item))
                
        if len(results) > max_items:
            summary.append(f"... and {len(results) - max_items} more items")
            
        return "; ".join(summary)

    def analyze_context(self, session_id: str) -> Dict[str, Any]:
        """
        Analyze context to identify patterns and trends
        
        Args:
            session_id: Unique identifier for the conversation
            
        Returns:
            Dictionary containing context analysis
        """
        if session_id not in self.conversation_contexts:
            return {"patterns": [], "topic_focus": None}
            
        interactions = self.conversation_contexts[session_id]
        
        # Identify common topics/entities
        topics = {}
        for interaction in interactions:
            words = interaction.query.lower().split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    topics[word] = topics.get(word, 0) + 1
                    
        # Sort topics by frequency
        common_topics = sorted(
            topics.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # Identify query patterns
        patterns = []
        if any("compare" in i.query.lower() for i in interactions):
            patterns.append("comparative_analysis")
        if any("trend" in i.query.lower() for i in interactions):
            patterns.append("trend_analysis")
        if any("distribution" in i.query.lower() for i in interactions):
            patterns.append("distribution_analysis")
            
        return {
            "patterns": patterns,
            "topic_focus": [topic for topic, _ in common_topics] if common_topics else None,
            "interaction_count": len(interactions),
            "has_visualizations": any(i.visualization_type for i in interactions)
        }

    def clear_context(self, session_id: str) -> None:
        """
        Clear context for a given session
        
        Args:
            session_id: Unique identifier for the conversation
        """
        if session_id in self.conversation_contexts:
            del self.conversation_contexts[session_id]

    def export_context(self, session_id: str, format: str = "json") -> str:
        """
        Export context history in specified format
        
        Args:
            session_id: Unique identifier for the conversation
            format: Output format (currently supports 'json' only)
            
        Returns:
            Formatted string representation of context
        """
        if session_id not in self.conversation_contexts:
            return ""
            
        if format.lower() == "json":
            context_data = []
            for interaction in self.conversation_contexts[session_id]:
                context_data.append({
                    "timestamp": interaction.timestamp,
                    "query": interaction.query,
                    "sql_query": interaction.sql_query,
                    "results": interaction.results,
                    "explanation": interaction.explanation,
                    "visualization_type": interaction.visualization_type,
                    "visualization_data": interaction.visualization_data
                })
            return json.dumps(context_data, indent=2)
            
        raise ValueError(f"Unsupported export format: {format}")