# visualization_module.py
import re
import logging
from typing import List, Dict, Any
from nl_converter import NLConverter, ContextManager 

logger = logging.getLogger(__name__)

class VisualizationModule:
    def process_visualization(self, query_result: Dict[str, Any], natural_query: str) -> Dict[str, Any]:
        """
        Simplified visualization processing.
        If the results contain more than two rows, prepare data for visualization.
        """
        try:
            # Skip visualization if there are fewer than two rows
            if not query_result["results"] or len(query_result["results"]) <= 1:
                return {"success": False, "visualization": None, "reason": "Insufficient data for visualization."}

            # Basic data validation
            if not self.validate_data(query_result["results"], query_result["columns"]):
                return {"success": False, "visualization": None, "reason": "Invalid data format."}

            # Prepare data for visualization (e.g., bar chart)
            viz_data = self.prepare_visualization_data(
                query_result["results"],
                query_result["columns"],
                "bar",  # Default to bar chart for simplicity
                natural_query
            )

            return {"success": True, "visualization": viz_data} if viz_data else {"success": False, "visualization": None}
        except Exception as e:
            logger.error(f"Error processing visualization: {str(e)}")
            return {"success": False, "visualization": None, "reason": str(e)}

    def validate_data(self, results: List[List[Any]], columns: List[str]) -> bool:
        """
        Simple data validation.
        """
        return bool(results and columns and len(results) > 1)

    def prepare_visualization_data(self, results: List[List[Any]], columns: List[str], chart_type: str, title: str) -> Dict[str, Any]:
        """
        Prepare data for visualization.
        """
        try:
            # Extract data for visualization
            x_values = [row[0] for row in results]
            y_values = [row[1] for row in results]

            return {
                "type": chart_type,
                "data": {"x": x_values, "y": y_values},
                "title": title,
                "x_label": columns[0],
                "y_label": columns[1]
            }
        except IndexError as e:
            logger.error(f"Error preparing visualization data: {str(e)}")
            return None

# Main Code Integration
class NLConverterWithVisualization(NLConverter):
    def __init__(self, api_key: str, context_manager: ContextManager):
        super().__init__(api_key, context_manager)
        self.visualization_module = VisualizationModule()

    def convert_to_natural_language(self, query_result: Dict[str, Any], original_query: str) -> Dict[str, Any]:
        """
        Enhanced method to include visualization processing.
        """
        response = super().convert_to_natural_language(query_result, original_query)

        if response["success"]:
            # Add visualization if applicable
            visualization = self.visualization_module.process_visualization(query_result, original_query)
            response["visualization"] = visualization.get("visualization") if visualization["success"] else None

        return response
